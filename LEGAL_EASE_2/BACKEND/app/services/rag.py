"""RAG pipeline: retrieval + context construction + multi-LLM generation."""

import asyncio
import re
from typing import List, Optional

import httpx
from google import genai
from google.genai import types

from app.core.config import settings
from app.services.embedder import embed_query
from app.services.vectorstore import query_similar_chunks

# Initialize Gemini client
_gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# ── Multi-model fallback pipeline ──────────────────────────────────────────
# Each model has its own free-tier quota (per-day + per-minute).
# When one is rate-limited we fall through to the next.
LLM_MODELS = [
    "gemini-2.5-flash-lite",   # primary — fastest
    "gemini-2.0-flash",        # fallback 1
    "gemini-2.5-flash",        # fallback 2 (separate daily quota)
    "gemini-2.0-flash-lite",   # fallback 3
]

# Global semaphore: only 1 LLM call at a time across the whole app.
# Prevents parallel comparison aspects from burning through quotas simultaneously.
_llm_semaphore = asyncio.Semaphore(1)

# ── Ollama local LLM client (shared) ─────────────────────────────────────
_ollama_gen_client: Optional[httpx.AsyncClient] = None


def _get_ollama_gen_client() -> httpx.AsyncClient:
    """Return a reusable async httpx client for Ollama generation."""
    global _ollama_gen_client
    if _ollama_gen_client is None or _ollama_gen_client.is_closed:
        _ollama_gen_client = httpx.AsyncClient(timeout=180.0)
    return _ollama_gen_client


async def warmup_ollama():
    """Pre-load the Ollama generation model into memory so first real call is fast."""
    if not settings.OLLAMA_GEN_ENABLED:
        return
    try:
        client = _get_ollama_gen_client()
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": settings.OLLAMA_GEN_MODEL,
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "options": {"num_predict": 1},  # generate 1 token just to load model
            },
            timeout=120.0,
        )
        if resp.status_code == 200:
            print(f"[OK] Ollama model '{settings.OLLAMA_GEN_MODEL}' warmed up and ready")
        else:
            print(f"[WARN] Ollama warmup returned {resp.status_code}")
    except Exception as e:
        print(f"[WARN] Ollama warmup skipped ({type(e).__name__}: {e})")


def _build_ollama_messages(contents, system_instruction: Optional[str] = None) -> list:
    """Convert contents (str / list / Gemini Content objects) to Ollama chat messages."""
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})

    if isinstance(contents, str):
        messages.append({"role": "user", "content": contents})
    elif isinstance(contents, list):
        for item in contents:
            if hasattr(item, "role") and hasattr(item, "parts"):
                role = "user" if item.role == "user" else "assistant"
                text = item.parts[0].text if item.parts else ""
                messages.append({"role": role, "content": text})
            elif isinstance(item, dict):
                messages.append(item)
            else:
                messages.append({"role": "user", "content": str(item)})
    else:
        messages.append({"role": "user", "content": str(contents)})
    return messages


async def _generate_with_ollama(
    *,
    contents,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    max_output_tokens: int = 1024,
    label: str = "LLM",
) -> Optional[str]:
    """
    Generate text using local Ollama model (qwen2.5:7b).
    Uses the /api/chat endpoint with message format.
    Automatically caps output tokens and uses a smaller context window for speed.
    Returns None if Ollama is unavailable or fails.
    """
    if not settings.OLLAMA_GEN_ENABLED:
        return None

    # Speed optimizations: cap output at 300 tokens (≈12-15s at ~13 tok/s)
    ollama_max_tokens = min(max_output_tokens, 300)

    try:
        messages = _build_ollama_messages(contents, system_instruction)
        client = _get_ollama_gen_client()
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": settings.OLLAMA_GEN_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": ollama_max_tokens,
                    "num_ctx": 2048,        # smaller context window = faster
                    "repeat_penalty": 1.1,  # avoid repetition loops
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("message", {}).get("content", "").strip()
        if text:
            dur = data.get("total_duration", 0) / 1e9
            toks = data.get("eval_count", 0)
            print(f"[{label}] [OK] Ollama ({settings.OLLAMA_GEN_MODEL}) {toks} tokens in {dur:.1f}s")
            return text
        print(f"[{label}] Ollama returned empty response")
        return None

    except httpx.TimeoutException:
        print(f"[{label}] Ollama ({settings.OLLAMA_GEN_MODEL}) timed out (model may be loading)")
        return None
    except httpx.ConnectError:
        print(f"[{label}] Ollama not reachable at {settings.OLLAMA_BASE_URL}")
        return None
    except Exception as e:
        print(f"[{label}] Ollama ({settings.OLLAMA_GEN_MODEL}) {type(e).__name__}: {e}")
        return None


def _parse_retry_delay(error_str: str) -> Optional[float]:
    """Extract the retryDelay seconds from a Gemini RESOURCE_EXHAUSTED error."""
    # Matches patterns like: 'retryDelay': '31s'  or  retryDelay: "53.727s"
    m = re.search(r"retry(?:\s*in\s+|Delay['\"]?:\s*['\"]?)(\d+(?:\.\d+)?)", error_str, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


async def _generate_with_fallback(
    *,
    contents,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    max_output_tokens: int = 1024,
    label: str = "LLM",
    ollama_contents=None,
    ollama_system: Optional[str] = None,
) -> Optional[str]:
    """
    Try each model in LLM_MODELS behind a global semaphore.
    Rate-limit errors skip to the next model immediately.
    If all exhausted, try local Ollama (with optional simplified prompt), then wait for Gemini retry.

    ollama_contents / ollama_system: optional shorter prompt for local model speed.
    """
    shortest_retry: Optional[float] = None

    async with _llm_semaphore:
        for model_name in LLM_MODELS:
            for attempt in range(2):
                try:
                    if system_instruction:
                        config = types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=temperature,
                            max_output_tokens=max_output_tokens,
                        )
                    else:
                        config = types.GenerateContentConfig(
                            temperature=temperature,
                            max_output_tokens=max_output_tokens,
                        )

                    response = _gemini_client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config,
                    )
                    text = response.text or ""
                    if text.strip():
                        if model_name != LLM_MODELS[0]:
                            print(f"[{label}] [OK] Succeeded with fallback: {model_name}")
                        return text
                    # Empty response — quick retry
                    print(f"[{label}] Empty from {model_name} ({attempt+1}/2)")
                    await asyncio.sleep(0.5)
                    continue

                except Exception as e:
                    error_str = str(e)
                    is_rate_limit = any(k in error_str for k in ("429", "RESOURCE_EXHAUSTED")) or "quota" in error_str.lower()

                    if is_rate_limit:
                        delay = _parse_retry_delay(error_str)
                        if delay and (shortest_retry is None or delay < shortest_retry):
                            shortest_retry = delay
                        print(f"[{label}] {model_name} rate-limited" + (f" (retry in {delay:.0f}s)" if delay else "") + ", next model...")
                        break  # next model
                    else:
                        print(f"[{label}] {model_name} error: {e}")
                        if attempt == 0:
                            await asyncio.sleep(1)
                            continue
                        break

        # All Gemini models exhausted — try local Ollama before giving up
        print(f"[{label}] All Gemini models exhausted, trying local Ollama...")
        ollama_result = await _generate_with_ollama(
            contents=ollama_contents or contents,
            system_instruction=ollama_system or system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            label=label,
        )
        if ollama_result:
            return ollama_result

        # Ollama also failed — wait for shortest Gemini retry delay, then final attempt
        wait = min(shortest_retry or 30, 60)
        print(f"[{label}] Ollama unavailable, waiting {wait:.0f}s for Gemini retry...")
        await asyncio.sleep(wait)

        # Final retry on whichever model has the shortest wait
        try:
            if system_instruction:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
            else:
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
            response = _gemini_client.models.generate_content(
                model=LLM_MODELS[0],
                contents=contents,
                config=config,
            )
            return (response.text or "").strip() or None
        except Exception as e:
            print(f"[{label}] Final retry failed: {e}")
            return None

SYSTEM_PROMPT = """You are a legal document assistant designed to analyze uploaded documents and provide structured, trustworthy, and user-friendly responses.

---

## CORE BEHAVIOR RULES

1. ALWAYS base your answers strictly on the uploaded document context.
2. If the answer is NOT found in the provided snippets but might be elsewhere in the document, encourage the user to ask for a summary or search specific terms.
3. If the answer is definitely NOT in the document, respond with:
   "This information is not explicitly available in the retrieved sections of the document."
4. If the query is unrelated to the document, respond with:
   "This query is outside the scope of the uploaded document."
5. DO NOT hallucinate or assume missing details.
6. High-level questions (like 'scope', 'purpose', 'summary') should be answered by synthesizing the available chunks.

---

## INTENT OVERRIDE (HIGH PRIORITY)

If the system provides an explicit intent (e.g., SUMMARY, CLAUSES, RISK_ANALYSIS, FINANCIAL, TERMINATION, OBLIGATIONS):

→ You MUST follow that mode strictly
→ Do NOT infer intent from user text
→ Do NOT mix multiple modes

Intent Mapping:

SUMMARY → High-level overview
CLAUSES → Extract important clauses
RISK_ANALYSIS → Identify risks with severity
FINANCIAL → Only payment/revenue terms
TERMINATION → Only termination conditions
OBLIGATIONS → Duties of each party

---

## RESPONSE MODES

A. SUMMARY MODE:
Explain:
• Purpose of agreement
• Parties involved
• Financial structure
• Duration
• Key obligations
Avoid minor operational details

B. CLAUSES MODE:
Extract and group:
• Payment Terms
• Termination
• Legal Obligations
• Rights & Responsibilities

C. RISK ANALYSIS MODE:
Identify:
• Financial risks
• Legal risks
• One-sided clauses
Mark severity: 🔴 High | 🟡 Medium | 🟢 Low

D. FINANCIAL MODE:
Focus only on:
• Payments
• Royalties
• Revenue sharing

E. TERMINATION MODE:
Focus only on:
• Termination triggers
• Notice period
• Post-termination effects

F. OBLIGATIONS MODE:
Clearly separate:
• Responsibilities of Party A
• Responsibilities of Party B

---

## RESPONSE STRUCTURE

Adapt structure based on intent:

1. If intent = SUMMARY:

🧠 Summary:
<2–4 lines simple explanation>

📌 Key Points:
• Clean bullet points
• Only important info

📍 Source References:
• Page number + section
• Example: (Page 6 – Payment Section)

2. If intent ≠ SUMMARY:

Start directly with the section title:
Example:
⚠️ Risk Analysis: <content>

📍 Source References: <references>

Rules:
• DO NOT repeat file names
• DO NOT dump raw chunks
• Keep answers clean and readable

---

## CITATION RULES

1. Every important claim must have a reference
2. Use inline citation format: (Page X – Section Name)
3. Avoid repeating the same source multiple times

---

## SMART SUGGESTIONS

🎯 Rule: Show max 2 contextual suggestions ONLY at the end of your response in the format: [Suggestion Text].
Example: [View Payment Terms] [Check Risks]
Suggestions must be based on actual document content and feel contextual.
"""

OLLAMA_SYSTEM_PROMPT = """You are a concise legal document assistant. 
Follow instructions for modes (SUMMARY, RISK, etc.) and always provide citations in format (Page X - Section).
Keep answers structured and professional."""

COMPARISON_PROMPT = """You are LexiChain, a legal document comparison assistant.
You MUST format your response using **Markdown**.

Compare the following documents on the legal aspect: **{aspect}**

## Required Response Structure:

### 1. Per-Document Analysis
For each document, provide:
- **Key Provision**: What the document says about "{aspect}" in 2–3 sentences
- **Relevant Clause**: Quote the most relevant clause text (in a `code block`)
- **Page Reference**: The page number where this was found
- **Strength of Coverage**: Rate as ✅ Strong | ⚠️ Partial | ❌ Missing

### 2. Side-by-Side Comparison Table
Create a markdown table comparing the key terms:
| Aspect Detail | Document 1 | Document 2 | ... |
|---|---|---|---|

### 3. Key Differences
Bullet points highlighting the most significant differences between the documents.

### 4. Risk Implications
Briefly note any risks arising from these differences (e.g., one document is more protective than the other).

### 5. Recommendation
One concise recommendation for the reviewing party.

If a document does not mention this aspect, state "**Not mentioned** — This document does not address {aspect}."

Context:
{context}"""

# Concise comparison prompt for local Ollama model (fast, focused output)
OLLAMA_COMPARISON_PROMPT = """Compare these contracts on **{aspect}**.

For each document give the key provision, then list differences and one risk note.
Use markdown. Keep response under 200 words.

{context}"""


def build_context_from_chunks(chunks: List[dict], doc_name_map: Optional[dict] = None) -> str:
    """Build a context string from retrieved chunks."""
    context_parts = []
    for i, chunk in enumerate(chunks):
        doc_id = chunk["metadata"].get("doc_id", "unknown")
        doc_name = (doc_name_map or {}).get(doc_id, f"Document {doc_id[:8]}")
        page = chunk["metadata"].get("page_number", "?")
        heading = chunk["metadata"].get("clause_heading", "General")

        context_parts.append(
            f"[Source: {doc_name} | Page {page} | Section: {heading}]\n{chunk['text']}"
        )

    return "\n\n---\n\n".join(context_parts)


async def rag_query(
    user_id: str,
    query: str,
    doc_ids: List[str],
    doc_name_map: Optional[dict] = None,
    chat_history: Optional[List[dict]] = None,
    intent: Optional[str] = None,
    top_k: int = 10,
) -> dict:
    # Special Case: Single Source of Truth for Risk Analysis (v7 Speed Optimization)
    if intent == "RISK":
        from app.models.document import LegalDocument
        risk_entries = []
        for doc_id in doc_ids:
            doc = await LegalDocument.find_one(LegalDocument.id == doc_id)
            if doc and doc.risk_results:
                risk_entries.append({
                    "name": doc.original_name,
                    "results": doc.risk_results
                })
        
        # v7 SPEED BYPASS: return ALL risks as structured markdown (no LLM needed)
        if risk_entries:
            entry = risk_entries[0]  # primary doc
            results = entry["results"]
            risks = results.get("risks", [])
            level = results.get("level", "Unknown")
            score = results.get("score", 0)
            breakdown = results.get("breakdown", {})

            # ── Structured markdown for chatbot: same data as Risk Engine panel ──
            sev_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}

            lines = [
                f"## ⚠️ Risk Analysis Summary",
                f"",
                f"**Risk Level:** {level} &nbsp;|&nbsp; **Score:** {score}%",
                f"**Breakdown:** 🔴 High: {breakdown.get('high', 0)} &nbsp;·&nbsp; 🟡 Medium: {breakdown.get('medium', 0)} &nbsp;·&nbsp; 🟢 Low: {breakdown.get('low', 0)}",
                f"",
                f"---",
                f"",
            ]

            for i, risk in enumerate(risks, 1):
                sev = risk.get("severity", "LOW")
                icon = sev_icon.get(sev, "⚪")
                lines += [
                    f"### {icon} {i}. {risk.get('title', 'Risk')} `{sev}`",
                    f"",
                    f"**Explanation:** {risk.get('explanation', '')}",
                    f"",
                    f"**Impact:** {risk.get('impact', '')}",
                    f"",
                    f"**Suggestion:** {risk.get('suggestion', '')}",
                    f"",
                    f"📍 *Source: {risk.get('source', 'General')}*",
                    f"",
                    f"---",
                    f"",
                ]

            answer = "\n".join(lines)

            return {
                "answer": answer,
                "citations": [],
                "retrieved_chunks": [],
                "risk_results": results,  # full SSOT object for embedded RiskAlerts UI
            }

    # Step 1: Embed the query
    query_vector = await embed_query(query)

    # Step 2: Retrieve relevant chunks (with distance filtering in vectorstore)
    chunks = query_similar_chunks(
        user_id=user_id,
        query_embedding=query_vector,
        top_k=top_k,
        doc_ids=doc_ids,
        max_distance=1.3,  # cosine distance threshold
    )

    if not chunks:
        return {
            "answer": "No relevant information found in the uploaded document(s). "
                      "Please ensure the document has been fully processed, or try rephrasing your question.",
            "citations": [],
            "retrieved_chunks": [],
        }

    # Step 2b: Use top 6 most relevant chunks for generation to ensure high-level context
    generation_chunks = chunks[:6]

    # Step 3: Build context from top generation chunks
    context = build_context_from_chunks(generation_chunks, doc_name_map)

    # Step 4: Build conversation messages
    messages = []
    if chat_history:
        for msg in chat_history[-4:]:  # Last 4 messages for context
            messages.append({"role": msg["role"], "parts": [msg["content"]]})

    user_message = f"""Context from legal documents:

{context}

---

{f'[SYSTEM INTENT: {intent}]' if intent else ''}
User Question: {query}

Provide a concise, accurate answer with citations (document name, page number, exact clause text)."""

    # Step 5: Generate with multi-model fallback pipeline
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["parts"][0])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

    answer = await _generate_with_fallback(
        contents=contents,
        system_instruction=SYSTEM_PROMPT,
        temperature=0.2,
        max_output_tokens=1024,
        label="RAG",
        ollama_system=OLLAMA_SYSTEM_PROMPT,
    )

    if not answer:
        answer = "I'm currently experiencing high demand. Please try again in a minute."

    # Step 6: Build citations from retrieved chunks
    citations = []
    for chunk in chunks:
        doc_id = chunk["metadata"].get("doc_id", "")
        doc_name = (doc_name_map or {}).get(doc_id, f"Document {doc_id[:8]}")
        citations.append({
            "doc_name": doc_name,
            "page_number": chunk["metadata"].get("page_number"),
            "clause_text": chunk["text"][:300],  # Truncate for response
            "clause_type": chunk["metadata"].get("clause_heading", "General"),
        })

    # Find the consolidated risk_results if we are in RISK mode
    total_risk_results = None
    if intent == "RISK":
        # For simplicity in this demo, use the first document's results if multiple are present
        # In a real app, this would be a merged object.
        from app.models.document import LegalDocument
        doc = await LegalDocument.find_one(LegalDocument.id == doc_ids[0])
        if doc:
            total_risk_results = doc.risk_results

    return {
        "answer": answer,
        "citations": citations,
        "retrieved_chunks": chunks,
        "risk_results": total_risk_results,
    }


async def compare_documents(
    user_id: str,
    doc_ids: List[str],
    aspect: str,
    doc_name_map: Optional[dict] = None,
) -> dict:
    """
    Compare multiple documents on a specific aspect using RAG.
    
    Returns:
        {aspect, doc_results: [...], summary}
    """
    # Retrieve relevant chunks across all docs for this aspect
    query_vector = await embed_query(f"{aspect} clause terms conditions")

    all_doc_results = []

    for doc_id in doc_ids:
        chunks = query_similar_chunks(
            user_id=user_id,
            query_embedding=query_vector,
            top_k=4,
            doc_ids=[doc_id],
            max_distance=1.3,
        )

        doc_name = (doc_name_map or {}).get(doc_id, f"Document {doc_id[:8]}")

        if chunks:
            all_doc_results.append({
                "doc_id": doc_id,
                "doc_name": doc_name,
                "finding": chunks[0]["text"][:200],
                "page": chunks[0]["metadata"].get("page_number"),
                "clause_text": chunks[0]["text"][:400],
            })
        else:
            all_doc_results.append({
                "doc_id": doc_id,
                "doc_name": doc_name,
                "finding": "Not mentioned",
                "page": None,
                "clause_text": "",
            })

    # Generate comparison summary with LLM
    context = "\n\n".join(
        f"[{r['doc_name']}] (Page {r['page']}): {r['clause_text']}"
        for r in all_doc_results
    )

    # Full prompt for Gemini (detailed 5-section response)
    prompt = COMPARISON_PROMPT.format(aspect=aspect, context=context)

    # Concise prompt for Ollama fallback (fast, focused)
    ollama_prompt = OLLAMA_COMPARISON_PROMPT.format(aspect=aspect, context=context)

    summary_text = await _generate_with_fallback(
        contents=prompt,
        temperature=0.2,
        max_output_tokens=768,
        label=f"Compare:{aspect}",
        ollama_contents=ollama_prompt,
        ollama_system="You are a concise legal comparison expert. Use markdown. Keep response under 200 words.",
    )

    return {
        "aspect": aspect,
        "doc_results": all_doc_results,
        "summary": summary_text or "Unable to generate comparison due to rate limits. Please try again shortly.",
    }
