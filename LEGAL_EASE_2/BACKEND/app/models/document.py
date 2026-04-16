"""Document model for uploaded legal documents."""

from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document as BeanieDoc
from pydantic import BaseModel, Field


class ClauseInfo(BaseModel):
    """Embedded clause data."""
    pass


class DetectedClause(BaseModel):
    """Structured clause info embedded in document."""
    pass


class RiskFlag(BaseModel):
    """Risk flag embedded in document."""
    pass


class LegalDocument(BeanieDoc):
    user_id: str
    filename: str  # stored filename (uuid-based)
    original_name: str  # original upload name
    file_size: int = 0  # bytes
    page_count: int = 0
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="processing")  # "processing" | "ready" | "error"
    error_message: Optional[str] = None

    # Processing progress
    processing_step: Optional[str] = None  # current step name
    processing_progress: int = 0  # 0-100 percentage

    # Extracted content
    extracted_text_preview: Optional[str] = None  # first 500 chars
    total_chunks: int = 0

    # Analysis results
    clauses: List[dict] = Field(default_factory=list)
    # Each clause: {type, text, page_number, confidence, source}

    contract_type: Optional[str] = None  # "Non-Disclosure Agreement (NDA)", "Service Agreement", etc.

    risk_score: Optional[float] = None
    risk_level: Optional[str] = None  # "Low" | "Medium" | "High"
    risk_flags: List[dict] = Field(default_factory=list)
    # Each flag: {title, severity, explanation, impact, suggestion, source, confidence, detection_method, reason}

    risk_results: Optional[dict] = None
    # {score, level, breakdown: {high, medium, low, total_points}, risks: [...flags], observations: [string]}

    class Settings:
        name = "documents"
        indexes = ["user_id", "status"]

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "abc123",
                "filename": "uuid-file.pdf",
                "original_name": "NDA_Agreement.pdf",
                "status": "ready",
                "page_count": 12,
                "risk_score": 35.0,
                "risk_level": "Medium",
            }
        }
