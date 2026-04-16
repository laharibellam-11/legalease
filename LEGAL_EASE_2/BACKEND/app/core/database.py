"""MongoDB connection and Beanie ODM initialization."""

from typing import Optional

import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings

client: Optional[AsyncIOMotorClient] = None


async def connect_db():
    """Initialize MongoDB connection and Beanie ODM models."""
    global client
    is_local = "localhost" in settings.MONGODB_URI or "127.0.0.1" in settings.MONGODB_URI
    if is_local:
        client = AsyncIOMotorClient(settings.MONGODB_URI)
    else:
        client = AsyncIOMotorClient(settings.MONGODB_URI, tlsCAFile=certifi.where())
    
    # Import models here to avoid circular imports
    from app.models.user import User
    from app.models.document import LegalDocument
    from app.models.session import ChatSession

    db = client.get_default_database() if "/" in settings.MONGODB_URI.split("//")[-1] else client["lexichain"]
    
    await init_beanie(
        database=db,  # type: ignore[arg-type]
        document_models=[User, LegalDocument, ChatSession],
    )
    print("[OK] Connected to MongoDB")


async def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("[INFO] Disconnected from MongoDB")
