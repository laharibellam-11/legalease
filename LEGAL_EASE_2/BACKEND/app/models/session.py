"""Chat session model for storing conversation history."""

from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document
from pydantic import Field


class ChatMessage(dict):
    """A single chat message (stored as dict in list)."""
    pass


class ChatSession(Document):
    user_id: str
    doc_ids: List[str] = Field(default_factory=list)  # associated document IDs
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    messages: List[dict] = Field(default_factory=list)
    # Each message: {role: "user"|"assistant", content: str, citations: [...], timestamp: str}

    class Settings:
        name = "chat_sessions"
        indexes = ["user_id"]
