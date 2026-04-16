"""User model for MongoDB via Beanie ODM."""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import EmailStr, Field


class User(Document):
    email: EmailStr
    hashed_password: str
    full_name: str
    role: str = Field(default="user")  # "user" | "admin"
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None

    class Settings:
        name = "users"
        indexes = ["email"]

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "role": "user",
                "is_active": True,
            }
        }
