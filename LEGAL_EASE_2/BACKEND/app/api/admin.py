"""Admin API routes — user management, stats, document oversight."""

import os
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.core.dependencies import require_admin
from app.models.document import LegalDocument
from app.models.user import User
from app.schemas.schemas import AdminUserUpdate, PlatformStats, UserResponse
from app.services.vectorstore import delete_document_chunks

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(_admin: User = Depends(require_admin)):
    """Get aggregated platform statistics."""
    total_users = await User.count()
    total_documents = await LegalDocument.count()
    docs_processing = await LegalDocument.find(LegalDocument.status == "processing").count()
    docs_ready = await LegalDocument.find(LegalDocument.status == "ready").count()
    docs_error = await LegalDocument.find(LegalDocument.status == "error").count()

    # Average risk score across ready docs
    ready_docs = await LegalDocument.find(
        LegalDocument.status == "ready",
        LegalDocument.risk_score != None,
    ).to_list()

    avg_risk = None
    if ready_docs:
        scores = [d.risk_score for d in ready_docs if d.risk_score is not None]
        avg_risk = round(sum(scores) / len(scores), 1) if scores else None

    # Total extracted clauses and high-risk document count
    total_clauses = sum(len(d.clauses) for d in ready_docs if d.clauses)
    high_risk_count = sum(1 for d in ready_docs if d.risk_level == "High")

    return PlatformStats(
        total_users=total_users,
        total_documents=total_documents,
        documents_processing=docs_processing,
        documents_ready=docs_ready,
        documents_error=docs_error,
        avg_risk_score=avg_risk,
        total_clauses=total_clauses,
        high_risk_count=high_risk_count,
    )


@router.get("/users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
):
    """List all users with pagination."""
    users = await User.find_all().skip(skip).limit(limit).to_list()
    total = await User.count()

    return {
        "users": [
            UserResponse(
                id=str(u.id),
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                is_active=u.is_active,
                created_at=u.created_at,
            )
            for u in users
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update: AdminUserUpdate,
    _admin: User = Depends(require_admin),
):
    """Update a user's role or active status."""
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if update.is_active is not None:
        user.is_active = update.is_active
    if update.role is not None:
        if update.role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = update.role

    await user.save()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/documents")
async def list_all_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str = Query(None, alias="status"),
    _admin: User = Depends(require_admin),
):
    """List all documents across all users (admin view)."""
    query = LegalDocument.find_all()
    if status_filter:
        query = LegalDocument.find(LegalDocument.status == status_filter)

    docs = await query.skip(skip).limit(limit).to_list()
    total = await LegalDocument.count()

    # Build a user_id -> full_name lookup in a single batch query
    user_ids = list({d.user_id for d in docs})
    from beanie import PydanticObjectId
    users = await User.find({"_id": {"$in": [PydanticObjectId(uid) for uid in user_ids]}}).to_list()
    user_map: Dict[str, str] = {str(u.id): u.full_name for u in users}

    return {
        "documents": [
            {
                "id": str(d.id),
                "user_id": d.user_id,
                "full_name": user_map.get(d.user_id, "Unknown"),
                "original_name": d.original_name,
                "status": d.status,
                "upload_date": d.upload_date.isoformat(),
                "risk_score": d.risk_score,
                "risk_level": d.risk_level,
                "page_count": d.page_count,
                "clause_count": len(d.clauses) if d.clauses else 0,
            }
            for d in docs
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.delete("/documents/{document_id}")
async def admin_delete_document(
    document_id: str,
    _admin: User = Depends(require_admin),
):
    """Delete a document, its file on disk, and its vector embeddings."""
    doc = await LegalDocument.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # 1. Delete vector chunks from ChromaDB
    try:
        delete_document_chunks(doc.user_id, str(doc.id))
    except Exception:
        pass  # Collection may not exist

    # 2. Delete file from disk
    upload_dir = os.path.join(settings.UPLOAD_DIR, doc.user_id)
    file_path = os.path.join(upload_dir, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # 3. Delete MongoDB record
    await doc.delete()

    return {"detail": "Document deleted successfully"}
