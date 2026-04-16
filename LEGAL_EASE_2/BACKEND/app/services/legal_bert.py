"""Legal-BERT service for clause classification and semantic risk analysis.

Model: nlpaueb/legal-bert-base-uncased — trained on 12 GB of legal text
(EU legislation, UK legislation, ECHR cases, US court cases, contracts).

This module provides:
  - classify_clause(text) → {type, confidence}
  - classify_clauses_batch(texts) → [{type, confidence}, ...]
  - semantic_risk_score(text, clause_type) → {risk_level, risk_score, factors}
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple

import torch
from transformers import AutoTokenizer, AutoModel

from app.core.config import settings

# ── Clause types (same list used by clause_extractor.py) ─────────────
CLAUSE_TYPES = [
    "Termination",
    "Auto-Renewal",
    "Confidentiality",
    "Indemnity",
    "Intellectual Property",
    "Governing Law",
    "Non-Compete",
    "Payment",
    "Limitation of Liability",
    "Force Majeure",
    "Other",
]

# Template sentences for zero-shot cosine-similarity classification
_CLAUSE_TEMPLATES = {ct: f"This is a {ct.lower()} clause in a legal contract." for ct in CLAUSE_TYPES}

# ── Risk keyword library ─────────────────────────────────────────────
RISK_KEYWORDS: Dict[str, List[str]] = {
    "high": [
        "unlimited liability", "sole discretion", "irrevocable",
        "waive all rights", "indemnify and hold harmless",
        "consequential damages", "liquidated damages",
        "non-negotiable", "perpetual", "exclusive remedy",
        "automatic renewal", "unilateral termination",
        "no liability", "as-is", "without warranty",
        "binding arbitration", "class action waiver",
    ],
    "medium": [
        "best efforts", "reasonable efforts", "may terminate",
        "subject to change", "at its discretion", "commercially reasonable",
        "material breach", "cure period", "pro-rata",
        "limitation of liability", "cap on damages",
        "non-solicitation", "change of control",
    ],
    "low": [
        "mutual agreement", "written consent", "reasonable notice",
        "good faith", "standard terms", "industry standard",
        "mutual termination", "equal rights", "fair market value",
        "reasonable time", "both parties agree",
    ],
}

# Semantic risk probes for Legal-BERT
_RISK_PROBES = [
    ("This clause has very high legal risk and is unfavorable.", "high"),
    ("This clause has moderate legal risk with some concerns.", "medium"),
    ("This clause has low legal risk and is standard.", "low"),
    ("This clause is fair and balanced for both parties.", "balanced"),
]

# ── Clause-specific risk heuristics ──────────────────────────────────
_CLAUSE_RISK_CHECKS: Dict[str, List[Tuple[str, str, str]]] = {
    # (regex_or_keyword, severity_emoji, description)
    "Termination": [
        ("without cause|at any time|immediate(ly)?", "HIGH", "Allows termination without cause"),
        ("^(?!.*\\b(30|60|90)\\s*days).*notice", "MEDIUM", "Notice period may be insufficient"),
        ("non-refundable|cancellation fee", "HIGH", "Document mentions non-refundable cancellation fees"),
    ],
    "Indemnity": [
        ("unlimited|all damages|all losses", "HIGH", "Unlimited indemnification obligation"),
        ("^(?!.*mutual).*indemnif", "MEDIUM", "Indemnification may be one-sided"),
        ("solely liable|waive all rights", "HIGH", "Unbalanced indemnity distribution"),
    ],
    "Limitation of Liability": [
        ("no liability|excluded|disclaim", "HIGH", "Complete liability exclusion detected"),
        ("^(?!.*cap|.*limit).*liab", "MEDIUM", "No liability cap specified"),
        ("consequential|incidental|punitive", "MEDIUM", "Broad exclusion of consequential damages"),
    ],
    "Confidentiality": [
        ("perpetual|indefinite|no expir", "MEDIUM", "Indefinite confidentiality period"),
        ("^(?!.*return|.*destroy).*confid", "MEDIUM", "No data return/destruction clause"),
        ("absolute discretion", "HIGH", "Disclosure allowed at sole discretion of one party"),
    ],
    "Non-Compete": [
        ("worldwide|global", "HIGH", "Worldwide geographic scope — may be unenforceable"),
        ("([3-9]|\\d{2,})\\s*year", "HIGH", "Non-compete duration appears excessive"),
        ("any business|any capacity", "MEDIUM", "Scope of non-compete is overly broad"),
    ],
    "Force Majeure": [
        ("^(?!.*pandemic|.*epidemic).*force majeure", "MEDIUM", "Does not cover pandemic/epidemic events"),
        ("not include strike|exclude labor", "MEDIUM", "Labor disputes excluded from force majeure"),
    ],
    "Payment": [
        ("net\\s*(60|90|120)", "MEDIUM", "Extended payment terms detected"),
        ("automatic debit|pre-authorized", "MEDIUM", "Clause mandates automatic payment authorization"),
    ],
    "Auto-Renewal": [
        ("automatically renew|auto-renew", "MEDIUM", "Hidden auto-renewal clause found"),
        ("^(?!.*notice).*renew", "HIGH", "Renewal happens without mandatory notice"),
    ],
    "Intellectual Property": [
        ("solely owned by|exclusive ownership", "MEDIUM", "Potentially one-sided IP ownership"),
        ("irrevocable license", "HIGH", "Mandatory irrevocable license grant detected"),
    ],
    "Governing Law": [
        ("^(?!.*(delaware|new york|london|singapore)).*governing law", "MEDIUM", "Governing law in a potentially unfavorable jurisdiction"),
    ],
}


class LegalBertService:
    """Singleton service wrapping Legal-BERT for clause classification & risk."""

    def __init__(self):
        self._tokenizer: Any = None
        self._model: Any = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._clause_embeddings: Optional[torch.Tensor] = None
        self._risk_embeddings: Optional[torch.Tensor] = None
        self._ready = False

    # ── Lazy initialisation ──────────────────────────────────────────
    def _load(self):
        if self._ready:
            return
        print(f"[INFO] Loading Legal-BERT ({settings.LEGAL_BERT_MODEL}) ...")
        self._tokenizer = AutoTokenizer.from_pretrained(settings.LEGAL_BERT_MODEL)
        self._model = AutoModel.from_pretrained(settings.LEGAL_BERT_MODEL)
        self._model.to(self._device)
        self._model.eval()
        self._ready = True
        print("[OK] Legal-BERT loaded")

    # ── Low-level embedding (CLS pooling) ────────────────────────────
    @torch.no_grad()
    def _encode(self, texts: List[str]) -> torch.Tensor:
        self._load()
        inputs = self._tokenizer(
            texts, padding=True, truncation=True, max_length=512, return_tensors="pt",
        ).to(self._device)
        outputs = self._model(**inputs)
        return outputs.last_hidden_state[:, 0, :]  # [CLS]

    def _get_clause_embeddings(self) -> torch.Tensor:
        if self._clause_embeddings is None:
            templates = [_CLAUSE_TEMPLATES[ct] for ct in CLAUSE_TYPES]
            self._clause_embeddings = self._encode(templates)
        return self._clause_embeddings

    def _get_risk_embeddings(self) -> torch.Tensor:
        if self._risk_embeddings is None:
            probes = [p[0] for p in _RISK_PROBES]
            self._risk_embeddings = self._encode(probes)
        return self._risk_embeddings

    # ── Clause classification ────────────────────────────────────────
    def _classify_sync(self, text: str) -> Dict:
        text_emb = self._encode([text.lower()])
        clause_embs = self._get_clause_embeddings()
        sims = torch.nn.functional.cosine_similarity(
            text_emb.unsqueeze(1), clause_embs.unsqueeze(0), dim=2,
        ).squeeze(0)
        top_scores, top_idx = torch.topk(sims, k=min(3, len(CLAUSE_TYPES)))
        predictions = [
            {"type": CLAUSE_TYPES[idx], "confidence": round(score, 4)}
            for score, idx in zip(top_scores.tolist(), top_idx.tolist())
        ]
        return {
            "type": predictions[0]["type"],
            "confidence": predictions[0]["confidence"],
            "alternatives": predictions[1:],
        }

    async def classify_clause(self, text: str) -> Dict:
        return await asyncio.to_thread(self._classify_sync, text)

    def _classify_batch_sync(self, texts: List[str]) -> List[Dict]:
        results = []
        batch_size = 16
        clause_embs = self._get_clause_embeddings()

        for i in range(0, len(texts), batch_size):
            batch = [t.lower() for t in texts[i : i + batch_size]]
            text_embs = self._encode(batch)
            sims = torch.nn.functional.cosine_similarity(
                text_embs.unsqueeze(1), clause_embs.unsqueeze(0), dim=2,
            )
            for j, sim in enumerate(sims):
                top_scores, top_idx = torch.topk(sim, k=min(3, len(CLAUSE_TYPES)))
                preds = [
                    {"type": CLAUSE_TYPES[idx], "confidence": round(sc, 4)}
                    for sc, idx in zip(top_scores.tolist(), top_idx.tolist())
                ]
                results.append({
                    "type": preds[0]["type"],
                    "confidence": preds[0]["confidence"],
                    "alternatives": preds[1:],
                })
        return results

    async def classify_clauses_batch(self, texts: List[str]) -> List[Dict]:
        return await asyncio.to_thread(self._classify_batch_sync, texts)

    # ── Semantic risk scoring ────────────────────────────────────────
    def _semantic_risk_sync(self, text: str, clause_type: Optional[str] = None) -> Dict:
        text_lower = text.lower()

        # 1) Keyword-based scoring
        high_hits = [kw for kw in RISK_KEYWORDS["high"] if kw in text_lower]
        med_hits = [kw for kw in RISK_KEYWORDS["medium"] if kw in text_lower]
        low_hits = [kw for kw in RISK_KEYWORDS["low"] if kw in text_lower]
        keyword_score = min(100, len(high_hits) * 30 + len(med_hits) * 15 + len(low_hits) * 5)

        # 2) Legal-BERT semantic scoring
        text_emb = self._encode([text_lower])
        risk_embs = self._get_risk_embeddings()
        sims = torch.nn.functional.cosine_similarity(
            text_emb.unsqueeze(1), risk_embs.unsqueeze(0), dim=2,
        ).squeeze(0)
        probs = torch.softmax(sims * 5, dim=0).tolist()
        semantic_score = probs[0] * 100 + probs[1] * 60 + probs[2] * 20 + probs[3] * 10

        # 3) Combine (60% semantic, 40% keyword)
        combined = round(keyword_score * 0.4 + semantic_score * 0.6, 1)
        if combined >= 70:
            level = "HIGH"
        elif combined >= 40:
            level = "MEDIUM"
        else:
            level = "LOW"

        # 4) Build risk factors
        factors: List[str] = []
        if high_hits:
            factors.append(f"⚠️ High-risk terms: {', '.join(high_hits[:5])}")
        if med_hits:
            factors.append(f"⚡ Moderate-risk terms: {', '.join(med_hits[:5])}")
        if low_hits:
            factors.append(f"✅ Standard terms: {', '.join(low_hits[:3])}")

        # Clause-specific checks
        if clause_type:
            for pattern_str, emoji, desc in _CLAUSE_RISK_CHECKS.get(clause_type, []):
                if re.search(pattern_str, text_lower):
                    factors.append(f"{emoji} {desc}")

        return {
            "risk_level": level,
            "risk_score": combined,
            "keyword_score": keyword_score,
            "semantic_score": round(semantic_score, 1),
            "risk_factors": factors,
            "high_risk_terms": high_hits,
            "medium_risk_terms": med_hits,
        }

    async def semantic_risk_score(self, text: str, clause_type: Optional[str] = None) -> Dict:
        return await asyncio.to_thread(self._semantic_risk_sync, text, clause_type)


# ── Module-level singleton ───────────────────────────────────────────
legal_bert = LegalBertService()
