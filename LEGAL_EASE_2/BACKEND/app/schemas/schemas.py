"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ──────────────── Auth Schemas ────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


# ──────────────── Document Schemas ────────────────

class DocumentResponse(BaseModel):
    id: str
    original_name: str
    file_size: int
    page_count: int
    upload_date: datetime
    status: str
    processing_step: Optional[str] = None
    processing_progress: int = 0
    extracted_text_preview: Optional[str] = None
    total_chunks: int = 0
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    contract_type: Optional[str] = None
    clauses: List[dict] = []
    risk_flags: List[dict] = []
    risk_results: Optional[dict] = None
    # risk_results schema: {score, level, breakdown, risks, observations}


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


# ──────────────── Chat / Analysis Schemas ────────────────

class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    doc_ids: List[str] = Field(min_length=1, max_length=3)
    session_id: Optional[str] = None
    intent: Optional[str] = None


class Citation(BaseModel):
    doc_name: str
    page_number: Optional[int] = None
    clause_text: str
    clause_type: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation] = []
    session_id: str
    risk_results: Optional[dict] = None


class AnalysisSummaryResponse(BaseModel):
    doc_id: str
    doc_name: str
    page_count: int
    clauses: List[dict]
    contract_type: Optional[str] = None
    risk_score: float
    risk_level: str
    risk_flags: List[dict]
    risk_results: Optional[dict] = None


# ──────────────── Comparison Schemas ────────────────

class ComparisonRequest(BaseModel):
    doc_ids: List[str] = Field(min_length=2, max_length=3)
    aspects: List[str] = Field(
        default=["termination", "renewal", "confidentiality", "indemnity", "governing_law"]
    )


class ComparisonResult(BaseModel):
    aspect: str
    doc_results: List[dict]
    # Each: {doc_id, doc_name, finding, page, clause_text}
    summary: Optional[str] = None


class ComparisonResponse(BaseModel):
    results: List[ComparisonResult]


# ──────────────── Admin Schemas ────────────────

class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None


class PlatformStats(BaseModel):
    total_users: int
    total_documents: int
    documents_processing: int
    documents_ready: int
    documents_error: int
    avg_risk_score: Optional[float] = None
    total_clauses: int = 0
    high_risk_count: int = 0
