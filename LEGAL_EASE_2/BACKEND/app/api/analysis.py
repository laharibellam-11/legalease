"""Analysis and Chat API routes — RAG Q&A and document summaries."""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.models.document import LegalDocument
from app.models.session import ChatSession
from app.models.user import User
from app.schemas.schemas import (
    AnalysisSummaryResponse,
    ChatRequest,
    ChatResponse,
    Citation,
)
from app.services.rag import rag_query

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat_with_documents(request: Request, req: ChatRequest, user: User = Depends(get_current_user)):
    """
    Ask a natural-language question about uploaded documents.
    Uses RAG pipeline: embed query → retrieve chunks → LLM generation.
    """
    # Validate all doc_ids belong to user (parallel fetch)
    doc_name_map = {}
    docs = await asyncio.gather(*(LegalDocument.get(doc_id) for doc_id in req.doc_ids))
    for doc_id, doc in zip(req.doc_ids, docs):
        if not doc or doc.user_id != str(user.id):
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        if doc.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Document '{doc.original_name}' is still processing. Please wait.",
            )
        doc_name_map[doc_id] = doc.original_name

    # Get or create chat session
    session = None
    chat_history = []
    if req.session_id:
        session = await ChatSession.get(req.session_id)
        if session and session.user_id == str(user.id):
            chat_history = session.messages
        else:
            session = None

    if not session:
        session = ChatSession(
            user_id=str(user.id),
            doc_ids=req.doc_ids,
            title=req.query[:80],
        )
        await session.insert()

    # Add user message to history
    query_text = req.query
    if req.intent:
        intent_map = {
            "SUMMARY": "Provide a high-level summary of the main points in the uploaded document(s).",
            "RISK": "Identify and analyze the primary legal risks, liabilities, and potential pitfalls.",
            "CLAUSES": "List and briefly explain the most critical clauses and provisions.",
            "FINANCIAL": "What are the financial terms, payment obligations, and monetary implications?",
            "TERMINATION": "Explain the termination rights and exit clauses for both parties.",
            "OBLIGATIONS": "What are the key affirmative and negative obligations of each party?",
        }
        query_text = intent_map.get(req.intent, req.query)

    session.messages.append({
        "role": "user",
        "content": query_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Run RAG pipeline
    result = await rag_query(
        user_id=str(user.id),
        query=query_text,
        doc_ids=req.doc_ids,
        doc_name_map=doc_name_map,
        chat_history=chat_history,
        intent=req.intent,
    )

    # Add assistant message to history
    session.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "citations": result["citations"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    session.updated_at = datetime.now(timezone.utc)
    await session.save()

    # Build response citations
    citations = [
        Citation(
            doc_name=c["doc_name"],
            page_number=c.get("page_number"),
            clause_text=c["clause_text"],
            clause_type=c.get("clause_type"),
        )
        for c in result["citations"]
    ]

    return ChatResponse(
        answer=result["answer"],
        citations=citations,
        session_id=str(session.id),
        risk_results=result.get("risk_results"),
    )


@router.get("/{doc_id}/summary", response_model=AnalysisSummaryResponse)
@limiter.limit("30/minute")
async def get_analysis_summary(request: Request, doc_id: str, user: User = Depends(get_current_user)):
    """Get clause extraction and risk analysis summary for a document."""
    doc = await LegalDocument.get(doc_id)
    if not doc or doc.user_id != str(user.id):
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status != "ready":
        raise HTTPException(status_code=400, detail="Document is still processing")

    # Synthesize risk_results if missing for older documents
    risk_results = doc.risk_results
    if not risk_results and doc.risk_score is not None:
        risk_results = {
            "score": doc.risk_score,
            "level": doc.risk_level or "Unknown",
            "breakdown": {
                "high": sum(1 for f in (doc.risk_flags or []) if f.get("severity") == "HIGH"),
                "medium": sum(1 for f in (doc.risk_flags or []) if f.get("severity") == "MEDIUM"),
                "low": sum(1 for f in (doc.risk_flags or []) if f.get("severity") == "LOW"),
            },
            "risks": doc.risk_flags or [],
            "contract_type": doc.contract_type or "General Agreement"
        }

    return AnalysisSummaryResponse(
        doc_id=str(doc.id),
        doc_name=doc.original_name,
        page_count=doc.page_count,
        clauses=doc.clauses,
        contract_type=doc.contract_type or "General Agreement",
        risk_score=doc.risk_score or 0,
        risk_level=doc.risk_level or "Unknown",
        risk_flags=doc.risk_flags,
        risk_results=risk_results,
    )


@router.get("/sessions", response_model=list)
async def list_chat_sessions(user: User = Depends(get_current_user)):
    """List all chat sessions for the current user."""
    sessions = await ChatSession.find(
        ChatSession.user_id == str(user.id)
    ).sort("-updated_at").to_list()

    return [
        {
            "id": str(s.id),
            "title": s.title,
            "doc_ids": s.doc_ids,
            "message_count": len(s.messages),
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_chat_session(session_id: str, user: User = Depends(get_current_user)):
    """Get full chat history for a session."""
    session = await ChatSession.get(session_id)
    if not session or session.user_id != str(user.id):
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": str(session.id),
        "title": session.title,
        "doc_ids": session.doc_ids,
        "messages": session.messages,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }
