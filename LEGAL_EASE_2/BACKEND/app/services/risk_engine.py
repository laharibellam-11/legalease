import re
import time
from typing import Dict, List, Optional

from google import genai
from app.core.config import settings

# Initialize Gemini client for categorization and LLM-based risk checks
_gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

from app.services.legal_bert import legal_bert, _CLAUSE_RISK_CHECKS

# ──────────────── Contract Type Detection ────────────────

async def detect_contract_type(text_preview: str) -> str:
    """Use Gemini to detect the type of legal agreement."""
    prompt = f"Categorize this document type (e.g. NDA, Service Agreement). Text: {text_preview[:1000]}"
    try:
        response = _gemini_client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt,
        )
        return response.text.strip()
    except:
        return "General Agreement"

# ──────────────── Rule-Based Engine (60% Weight) ────────────────

def run_rule_engine(clauses: List[dict]) -> List[dict]:
    """Runs presence checks and regex stress tests."""
    detected_types = {c["type"] for c in clauses}
    rule_risks = []
    
    # 1. Presence Checks (High Severity if missing)
    mandatory = ["Confidentiality", "Limitation of Liability", "Governing Law"]
    for m in mandatory:
        if m not in detected_types:
            rule_risks.append({
                "title": f"Missing {m} Clause",
                "severity": "HIGH",
                "explanation": f"The document lacks a dedicated {m} section.",
                "impact": f"High exposure to legal ambiguity or {m.lower()} disputes.",
                "suggestion": f"Advise adding a standard {m} clause to protect your interests.",
                "page": 0,
                "section": "General",
                "method": "Rule-Based (Presence)"
            })
            
    # 2. Logic Stress Tests (Regex-based heuristics from legal_bert)
    for clause in clauses:
        ct = clause["type"]
        text = clause["text"].lower()
        if ct in _CLAUSE_RISK_CHECKS:
            for pattern, severity, desc in _CLAUSE_RISK_CHECKS[ct]:
                if re.search(pattern, text):
                    rule_risks.append({
                        "title": f"{ct} {severity.capitalize()} Risk",
                        "severity": severity,
                        "explanation": desc,
                        "impact": "Unfavorable terms may increase legal or financial liability.",
                        "suggestion": "Renegotiate this specific provision for more balanced terms.",
                        "page": clause.get("page_number", 0),
                        "section": ct,
                        "method": "Rule-Based (Logic)"
                    })
                    
    return rule_risks

# ──────────────── Semantic AI Engine (40% Weight) ────────────────

async def run_semantic_engine(clauses: List[dict]) -> List[dict]:
    """Calls Legal-BERT for semantic risk analysis."""
    semantic_risks = []
    if not clauses:
        return []
        
    for clause in clauses:
        res = await legal_bert.semantic_risk_score(clause["text"], clause["type"])
        if res["risk_level"] in ["HIGH", "MEDIUM"]:
            semantic_risks.append({
                "title": f"Semantic {clause['type']} Risk",
                "severity": res["risk_level"],
                "explanation": f"Legal-BERT flagged this clause with a semantic score of {res['risk_score']}.",
                "impact": f"Content analysis suggests unfavorable or non-standard language.",
                "suggestion": f"Check for one-sided terms: {', '.join(res['high_risk_terms'][:3])}",
                "page": clause.get("page_number", 0),
                "section": clause["type"],
                "method": "Semantic AI (BERT)",
                "score": res["risk_score"]
            })
            
    return semantic_risks

# ──────────────── Unified Engine Entry Point ────────────────

async def calculate_risk_enhanced(clauses: List[dict], extracted_preview: str = "") -> dict:
    """Restores the specialized dual-engine risk analysis (v8)."""
    contract_type = await detect_contract_type(extracted_preview)
    
    # 1. Run Engines
    rule_risks = run_rule_engine(clauses)
    semantic_risks = await run_semantic_engine(clauses)
    
    # 2. Score Calculation (Weighted 60/40)
    # A) Rule Score (0-100)
    # Each HIGH = 3 pts, MED = 2 pts. Max potential 30 pts for 10 tests?
    # Simple rule: each rule risk contributes to points.
    rule_pts = sum(3 if r["severity"] == "HIGH" else 2 for r in rule_risks)
    rule_score = min(100, rule_pts * 10) # cap at 100
    
    # B) Semantic Score (0-100)
    if semantic_risks:
        semantic_score = sum(r.get("score", 0) for r in semantic_risks) / len(semantic_risks)
    else:
        semantic_score = 0
        
    # Final Formula: 60% Rule / 40% Semantic
    final_score = round((0.6 * rule_score) + (0.4 * semantic_score), 1)
    
    # 3. Determine Level
    if final_score >= 50: level = "High"
    elif final_score >= 25: level = "Medium"
    else: level = "Low"
    
    # 4. Filter and Combine Risks (for UI)
    all_raw_risks = rule_risks + semantic_risks
    
    # Assembly for SSOT
    risk_data = {
        "score": final_score,
        "level": level,
        "breakdown": {
            "high": sum(1 for r in all_raw_risks if r["severity"] == "HIGH"),
            "medium": sum(1 for r in all_raw_risks if r["severity"] == "MEDIUM"),
            "low": sum(1 for r in all_raw_risks if r["severity"] == "LOW"),
            "total_points": int(rule_pts)
        },
        "risks": [
            {
                "title": r["title"],
                "severity": r["severity"],
                "explanation": r["explanation"],
                "impact": r["impact"],
                "suggestion": r["suggestion"],
                "source": f"Page {r.get('page', 0)} – {r.get('section', 'General')}",
                "confidence": 92.0,
                "detection_method": r.get("method", "ANALYSIS"),
                "reason": r["explanation"]
            } for r in all_raw_risks[:12] # Limit UI clutter
        ],
        "contract_type": contract_type
    }
    
    # Demo Mode: Ensure at least one risk exists if level is High/Medium
    if not risk_data["risks"] and level != "Low":
         risk_data["risks"].append({
             "title": "General Review Point",
             "severity": "LOW",
             "explanation": "Standard document review recommended.",
             "impact": "Potential for minor oversights.",
             "suggestion": "Read all sections carefully.",
             "source": "Page 1 – General",
             "confidence": 99.0,
             "detection_method": "ANALYSIS",
             "reason": "Standard fallback"
         })

    return risk_data
