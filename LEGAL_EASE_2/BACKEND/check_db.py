"""Check MongoDB state."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def check():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client["lexichain"]
    collections = await db.list_collection_names()
    print("Collections:", collections)
    for col in collections:
        count = await db[col].count_documents({})
        print(f"  {col}: {count} docs")
    # Check document statuses
    async for doc in db["documents"].find({}, {"status": 1, "original_name": 1}):
        name = doc.get("original_name", "?")
        status = doc.get("status", "?")
        print(f"  Doc: {name} -> {status}")
    client.close()

asyncio.run(check())
