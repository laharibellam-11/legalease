"""Clause extraction using hybrid Legal-BERT + Regex approach.

When Legal-BERT is enabled (default), unmatched chunks are classified locally
using nlpaueb/legal-bert-base-uncased instead of making Gemini LLM API calls.
This removes rate-limit issues and improves accuracy on legal text.
The Gemini LLM path is kept as a fallback if Legal-BERT is disabled.
"""

import re
import time
from typing import Dict, List

from google import genai

from app.core.config import settings

# Initialize Gemini client (kept for fallback)
_gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# ──────────────── Regex Pattern Library ────────────────

CLAUSE_PATTERNS: Dict[str, List[re.Pattern]] = {
    "Termination": [
        re.compile(r"terminat(e|ion|ing)\s+(this\s+)?(agreement|contract)", re.I),
        re.compile(r"termination\s+for\s+(cause|convenience)", re.I),
        re.compile(r"right\s+to\s+terminate", re.I),
        re.compile(r"upon\s+termination", re.I),
        re.compile(r"cancel(lation)?\s+of\s+(this\s+)?(agreement|contract)", re.I),
        re.compile(r"(agreement|contract)\s+shall\s+(automatically\s+)?terminate", re.I),
        re.compile(r"either\s+party\s+may\s+terminate", re.I),
        re.compile(r"expiry\s+(of|and)\s+(this\s+)?(agreement|term)", re.I),
    ],
    "Auto-Renewal": [
        re.compile(r"renew\s+automatically", re.I),
        re.compile(r"shall\s+(automatically\s+)?renew", re.I),
        re.compile(r"auto[- ]?renew(al|ing)?", re.I),
        re.compile(r"unless\s+(either\s+party\s+)?terminat", re.I),
        re.compile(r"successive\s+(renewal\s+)?term", re.I),
        re.compile(r"extend(ed)?\s+(for|by)\s+(an?\s+)?additional\s+(period|term)", re.I),
        re.compile(r"renewal\s+term", re.I),
    ],
    "Confidentiality": [
        re.compile(r"confidential(ity)?\s+(information|obligation|agreement|clause)", re.I),
        re.compile(r"non[- ]?disclosure", re.I),
        re.compile(r"proprietary\s+information", re.I),
        re.compile(r"shall\s+not\s+disclose", re.I),
        re.compile(r"keep\s+(strictly\s+)?confidential", re.I),
        re.compile(r"trade\s+secret", re.I),
        re.compile(r"disclos(e|ing|ure)\s+(any\s+)?confidential", re.I),
    ],
    "Indemnity": [
        re.compile(r"indemnif(y|ication|ied|ying)", re.I),
        re.compile(r"hold\s+harmless", re.I),
        re.compile(r"defend\s+and\s+indemnify", re.I),
        re.compile(r"indemnify\s+(and\s+)?hold\s+(the\s+)?(other\s+)?party", re.I),
        re.compile(r"indemnified\s+part(y|ies)", re.I),
    ],
    "Intellectual Property": [
        re.compile(r"intellectual\s+property(\s+rights)?", re.I),
        re.compile(r"(patent|copyright|trademark)s?", re.I),
        re.compile(r"work\s+product", re.I),
        re.compile(r"ownership\s+of\s+(all\s+)?(work|deliverable|ip)", re.I),
        re.compile(r"work(s)?\s+made\s+for\s+hire", re.I),
        re.compile(r"proprietary\s+rights", re.I),
    ],
    "Governing Law": [
        re.compile(r"govern(ed|ing)\s+(by\s+)?(the\s+)?law", re.I),
        re.compile(r"jurisdiction", re.I),
        re.compile(r"laws\s+of\s+(the\s+)?(state|republic|country)\s+of", re.I),
        re.compile(r"applicable\s+law", re.I),
        re.compile(r"subject\s+to\s+(the\s+)?(laws?|jurisdiction)", re.I),
        re.compile(r"courts?\s+of\s+competent\s+jurisdiction", re.I),
        re.compile(r"exclusive\s+jurisdiction", re.I),
    ],
    "Non-Compete": [
        re.compile(r"non[- ]?compet(e|ition|itive)", re.I),
        re.compile(r"restrictive\s+covenant", re.I),
        re.compile(r"shall\s+not\s+compete", re.I),
        re.compile(r"non[- ]?solicitation", re.I),
        re.compile(r"restraint\s+of\s+trade", re.I),
    ],
    "Payment": [
        re.compile(r"payment\s+(terms?|schedule|due|obligation)", re.I),
        re.compile(r"invoice|billing", re.I),
        re.compile(r"net\s+\d+\s+days", re.I),
        re.compile(r"compensation", re.I),
        re.compile(r"(fee|price|amount)\s+(shall\s+be|payable|due)", re.I),
        re.compile(r"late\s+payment", re.I),
        re.compile(r"(payable|paid)\s+(within|on|by)", re.I),
        re.compile(r"(monthly|annual|quarterly)\s+(fee|payment|installment)", re.I),
    ],
    "Limitation of Liability": [
        re.compile(r"limit(ation)?\s+of\s+liability", re.I),
        re.compile(r"shall\s+not\s+(be\s+)?liable", re.I),
        re.compile(r"in\s+no\s+event\s+shall", re.I),
        re.compile(r"aggregate\s+liability", re.I),
        re.compile(r"(maximum|total)\s+liability", re.I),
        re.compile(r"(direct|indirect|consequential|incidental|special|punitive)\s+damages", re.I),
        re.compile(r"exclusion\s+of\s+(liability|damages)", re.I),
    ],
    "Force Majeure": [
        re.compile(r"force\s+majeure", re.I),
        re.compile(r"act\s+of\s+god", re.I),
        re.compile(r"beyond\s+(the\s+)?(reasonable\s+)?control", re.I),
        re.compile(r"(war|flood|earthquake|pandemic|epidemic|natural\s+disaster)", re.I),
        re.compile(r"unforeseeable\s+(event|circumstance)", re.I),
    ],
    "Dispute Resolution": [
        re.compile(r"dispute\s+resolution", re.I),
        re.compile(r"(binding\s+)?arbitration", re.I),
        re.compile(r"mediat(e|ion)", re.I),
        re.compile(r"(settle|resolv)(e|ing)\s+(any\s+)?(dispute|controversy|claim)", re.I),
        re.compile(r"(alternative|amicable)\s+dispute", re.I),
    ],
    "Warranty": [
        re.compile(r"warrant(y|ies|s)\s+(that|of|and)", re.I),
        re.compile(r"represent(s|ation)?\s+and\s+warrant", re.I),
        re.compile(r"as[- ]?is", re.I),
        re.compile(r"without\s+warranty", re.I),
        re.compile(r"disclaim(s|er)?\s+.{0,30}warrant", re.I),
        re.compile(r"fitness\s+for\s+a\s+particular\s+purpose", re.I),
        re.compile(r"merchantability", re.I),
    ],
    "Assignment": [
        re.compile(r"assign(ment|able|s|ing)?\s+(of\s+)?(this\s+)?(agreement|contract|rights?)", re.I),
        re.compile(r"(shall\s+)?not\s+(be\s+)?assign(ed|able)", re.I),
        re.compile(r"transfer\s+(of\s+)?(this\s+)?(agreement|rights?)", re.I),
        re.compile(r"without\s+(the\s+)?(prior\s+)?(written\s+)?consent.{0,30}assign", re.I),
    ],
    "Data Protection": [
        re.compile(r"data\s+protect(ion|ing)", re.I),
        re.compile(r"personal\s+data", re.I),
        re.compile(r"gdpr|ccpa|data\s+privacy", re.I),
        re.compile(r"data\s+(processing|controller|processor|breach)", re.I),
        re.compile(r"privacy\s+polic(y|ies)", re.I),
    ],
    "Insurance": [
        re.compile(r"insurance\s+(coverage|polic(y|ies)|requirement)", re.I),
        re.compile(r"maintain\s+.{0,30}insurance", re.I),
        re.compile(r"(general\s+)?liability\s+insurance", re.I),
        re.compile(r"insured\s+(party|amount)", re.I),
    ],
    "Scope & Objective": [
        re.compile(r"(scope|objective|purpose|intent)\s+of\s+(this\s+)?(agreement|engagement|contract)", re.I),
        re.compile(r"nature\s+of\s+(the\s+)?services", re.I),
        re.compile(r"background\s+and\s+purpose", re.I),
        re.compile(r"statement\s+of\s+work", re.I),
    ],
}

# All recognized clause types (used for validation)
ALL_CLAUSE_TYPES = list(CLAUSE_PATTERNS.keys()) + ["Other"]

LLM_CLASSIFY_PROMPT = """Analyze the following legal text section and classify it into ONE of these clause types:
- Termination
- Auto-Renewal
- Confidentiality
- Indemnity
- Intellectual Property
- Governing Law
- Non-Compete
- Payment
- Limitation of Liability
- Force Majeure
- Dispute Resolution
- Warranty
- Assignment
- Data Protection
- Insurance
- Scope & Objective
- Other

Text:
\"\"\"{text}\"\"\"

Respond with ONLY the clause type name. Nothing else."""


def extract_clauses_regex(text: str, page_number: int = 1) -> List[dict]:
    """
    Extract clauses using regex pattern matching.
    Returns list of {type, text, page_number, confidence, source}.
    """
    clauses = []
    for clause_type, patterns in CLAUSE_PATTERNS.items():
        for pattern in patterns:
            matches = pattern.finditer(text)
            for match in matches:
                # Extract surrounding context (250 chars before and after)
                start = max(0, match.start() - 250)
                end = min(len(text), match.end() + 250)
                context = text[start:end].strip()

                clauses.append({
                    "type": clause_type,
                    "text": context,
                    "page_number": page_number,
                    "confidence": 0.75,
                    "source": "regex",
                    "match": match.group(),
                })

    # Deduplicate overlapping clauses of the same type
    return _deduplicate_clauses(clauses)


async def extract_clauses_llm(text: str, page_number: int = 1) -> List[dict]:
    """Classify a text section using Gemini LLM."""
    for attempt in range(3):
        try:
            response = _gemini_client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=LLM_CLASSIFY_PROMPT.format(text=text[:1000]),
            )
            clause_type = response.text.strip()

            # Validate it's a known type
            if clause_type not in ALL_CLAUSE_TYPES:
                clause_type = "Other"

            return [{
                "type": clause_type,
                "text": text[:500],
                "page_number": page_number,
                "confidence": 0.85,
                "source": "llm",
            }]
        except Exception as e:
            error_str = str(e)
            if ("429" in error_str or "quota" in error_str.lower()) and attempt < 2:
                time.sleep(2 * (2 ** attempt))
                continue
            print(f"LLM clause extraction error: {e}")
            return []
    return []


async def _batch_classify_legal_bert(unmatched: List[dict], on_progress=None) -> List[dict]:
    """Classify unmatched chunks using Legal-BERT (local, free, no rate limits).

    Falls back to Gemini LLM if Legal-BERT is disabled or fails.
    """
    from app.services.legal_bert import legal_bert

    if not unmatched:
        return []

    texts = [item["text"][:512] for item in unmatched]

    try:
        print(f"  [BERT] Legal-BERT classifying {len(texts)} chunks ...")
        classifications = await legal_bert.classify_clauses_batch(texts)

        results: List[dict] = []
        for item, cls in zip(unmatched, classifications):
            confidence = cls["confidence"]
            clause_type = cls["type"]

            # Filter out very low confidence — mark as Other to reduce noise
            if confidence < 0.45:
                clause_type = "Other"

            results.append({
                "type": clause_type,
                "text": item["text"][:500],
                "page_number": item["page"],
                "confidence": confidence,
                "source": "legal-bert",
            })

        if on_progress:
            try:
                await on_progress(100)
            except TypeError:
                on_progress(100)

        classified_count = sum(1 for r in results if r["type"] != "Other")
        print(f"  [OK] Legal-BERT classified {classified_count}/{len(results)} chunks (rest -> Other)")
        return results

    except Exception as e:
        print(f"  [WARN] Legal-BERT failed ({e}), falling back to Gemini LLM...")
        return await _batch_classify_llm(unmatched, on_progress)


async def _batch_classify_llm(unmatched: List[dict], on_progress=None) -> List[dict]:
    """Batch-classify multiple chunks in a single LLM call to save quota.
    
    Rate-limit aware: waits between requests to stay within free-tier limits
    (10 RPM for gemini-2.5-flash-lite).
    """
    if not unmatched:
        return []

    # Larger batch size = fewer API calls = fewer rate limits
    batch_size = 20
    all_results: List[dict] = []
    total_batches = (len(unmatched) + batch_size - 1) // batch_size

    for batch_idx, i in enumerate(range(0, len(unmatched), batch_size)):
        batch = unmatched[i:i + batch_size]
        numbered = "\n\n".join(
            f"[{j+1}] (page {item['page']}):\n\"\"\"{item['text'][:400]}\"\"\""
            for j, item in enumerate(batch)
        )
        valid = ", ".join(ALL_CLAUSE_TYPES)
        prompt = (
            f"Classify each numbered text snippet into exactly one clause type.\n"
            f"Valid types: {valid}\n\n{numbered}\n\n"
            f"Respond with ONLY a numbered list like:\n1. Termination\n2. Other\n"
            f"No extra text."
        )

        success = False
        for attempt in range(5):  # more retries with longer waits
            try:
                # Rate-limit: wait between requests (10 RPM = 1 req per 7s)
                if batch_idx > 0 and attempt == 0:
                    time.sleep(7)

                response = _gemini_client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=prompt,
                )
                lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]
                for j, item in enumerate(batch):
                    clause_type = "Other"
                    for line in lines:
                        if line.startswith(f"{j+1}.") or line.startswith(f"{j+1})"):
                            parsed = line.split(".", 1)[-1].split(")", 1)[-1].strip()
                            if parsed in ALL_CLAUSE_TYPES:
                                clause_type = parsed
                            break
                    all_results.append({
                        "type": clause_type,
                        "text": item["text"][:500],
                        "page_number": item["page"],
                        "confidence": 0.85,
                        "source": "llm",
                    })
                success = True
                pct = int((batch_idx + 1) / total_batches * 100)
                print(f"  LLM batch {batch_idx+1}/{total_batches} done ({pct}%)")
                if on_progress:
                    on_progress(pct)
                break  # success
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    # Parse retry delay from error if available
                    retry_delay = 15 * (attempt + 1)  # 15s, 30s, 45s, 60s, 75s
                    import re as _re
                    delay_match = _re.search(r"retryDelay.*?(\d+)", error_str)
                    if delay_match:
                        retry_delay = int(delay_match.group(1)) + 2  # add buffer
                    print(f"  Rate limited, waiting {retry_delay}s (attempt {attempt+1}/5)...")
                    time.sleep(retry_delay)
                    continue
                print(f"LLM batch clause extraction error: {e}")
                break

        if not success:
            # Fall back: mark all as "Other"
            for item in batch:
                all_results.append({
                    "type": "Other",
                    "text": item["text"][:500],
                    "page_number": item["page"],
                    "confidence": 0.3,
                    "source": "llm_fallback",
                })

    return all_results


async def extract_clauses_hybrid(
    chunks: List[dict],
    on_progress=None,
) -> List[dict]:
    """
    Hybrid clause extraction: regex on all chunks + batched LLM on ambiguous ones.
    Returns deduplicated, merged clause list.
    """
    all_clauses = []
    unmatched = []  # chunks that regex couldn't classify

    for chunk in chunks:
        text = chunk["text"]
        page = chunk.get("page_number", 1)

        # Step 1: Regex extraction
        regex_clauses = extract_clauses_regex(text, page)

        if regex_clauses:
            all_clauses.extend(regex_clauses)
        else:
            unmatched.append({"text": text, "page": page})

    # Step 2: Classify unmatched chunks — Legal-BERT (default) or Gemini LLM
    if unmatched:
        if settings.LEGAL_BERT_ENABLED:
            print(f"  [BERT] Legal-BERT classifying {len(unmatched)} unmatched chunks...")
            bert_clauses = await _batch_classify_legal_bert(unmatched, on_progress)
            all_clauses.extend(bert_clauses)
        else:
            print(f"  LLM classifying {len(unmatched)} unmatched chunks in batches of 20...")
            llm_clauses = await _batch_classify_llm(unmatched, on_progress)
            all_clauses.extend(llm_clauses)
    elif on_progress:
        try:
            await on_progress(100)
        except TypeError:
            on_progress(100)

    # Filter out Other clauses with very low confidence (noise)
    filtered = [c for c in all_clauses if not (c["type"] == "Other" and c.get("confidence", 0) < 0.4)]

    return _deduplicate_clauses(filtered)


def _deduplicate_clauses(clauses: List[dict]) -> List[dict]:
    """Remove duplicate clauses with overlapping text on the same page.

    Uses (type, page_number, text_fingerprint) as key to allow the SAME type
    to appear on different pages or with genuinely different text content.
    """
    seen = set()
    unique = []
    for clause in clauses:
        # Use short text fingerprint to distinguish different occurrences
        text_sig = clause.get("text", "")[:80].strip().lower()
        key = (clause["type"], clause.get("page_number", 0), hash(text_sig))
        if key not in seen:
            seen.add(key)
            unique.append(clause)
    return unique
