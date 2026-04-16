"""Reset document status for reprocessing."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def reset():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client["lexichain"]
    result = await db.documents.update_many(
        {"status": "ready"},
        {"$set": {"status": "uploaded"}}
    )
    print(f"Reset {result.modified_count} docs to Uploaded")
    client.close()

asyncio.run(reset())
