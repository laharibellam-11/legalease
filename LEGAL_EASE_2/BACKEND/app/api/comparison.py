"""Multi-document comparison API routes."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List

from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.models.document import LegalDocument
from app.models.user import User
from app.schemas.schemas import ComparisonRequest, ComparisonResponse, ComparisonResult
from app.services.rag import compare_documents

router = APIRouter(prefix="/api/comparison", tags=["Comparison"])


# ── Schema for single-aspect comparison ──────────────────────────────────
class SingleAspectRequest(BaseModel):
    doc_ids: List[str] = Field(min_length=2, max_length=3)
    aspect: str


@router.post("/compare-one", response_model=ComparisonResult)
@limiter.limit("15/minute")
async def compare_one_aspect(
    request: Request,
    req: SingleAspectRequest,
    user: User = Depends(get_current_user),
):
    """
    Compare 2–3 documents on a SINGLE legal aspect.
    Frontend calls this per-aspect to stream results progressively.
    """
    doc_name_map = {}
    docs = await asyncio.gather(*(LegalDocument.get(doc_id) for doc_id in req.doc_ids))
    for doc_id, doc in zip(req.doc_ids, docs):
        if not doc or doc.user_id != str(user.id):
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        if doc.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Document '{doc.original_name}' is still processing.",
            )
        doc_name_map[doc_id] = doc.original_name

    raw = await compare_documents(
        user_id=str(user.id),
        doc_ids=req.doc_ids,
        aspect=req.aspect,
        doc_name_map=doc_name_map,
    )

    return ComparisonResult(
        aspect=raw["aspect"],
        doc_results=raw["doc_results"],
        summary=raw.get("summary"),
    )


@router.post("/compare", response_model=ComparisonResponse)
@limiter.limit("10/minute")
async def compare_docs(request: Request, req: ComparisonRequest, user: User = Depends(get_current_user)):
    """
    Compare 2–3 documents across selected legal aspects.
    Returns side-by-side findings with LLM-generated diff summaries.
    """
    # Validate documents (parallel fetch)
    doc_name_map = {}
    docs = await asyncio.gather(*(LegalDocument.get(doc_id) for doc_id in req.doc_ids))
    for doc_id, doc in zip(req.doc_ids, docs):
        if not doc or doc.user_id != str(user.id):
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        if doc.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Document '{doc.original_name}' is still processing.",
            )
        doc_name_map[doc_id] = doc.original_name

    # Compare aspects concurrently — the global _llm_semaphore in rag.py
    # ensures only 1 Gemini call runs at a time to preserve quota.
    async def compare_one(aspect):
        return await compare_documents(
            user_id=str(user.id),
            doc_ids=req.doc_ids,
            aspect=aspect,
            doc_name_map=doc_name_map,
        )

    raw_results = await asyncio.gather(*(compare_one(a) for a in req.aspects))

    results = [
        ComparisonResult(
            aspect=r["aspect"],
            doc_results=r["doc_results"],
            summary=r.get("summary"),
        )
        for r in raw_results
    ]

    return ComparisonResponse(results=results)
