import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def clean():
    c = AsyncIOMotorClient("mongodb://localhost:27017/lexichain")
    await c.lexichain.documents.drop()
    print("Dropped documents collection to fix sync!")

asyncio.run(clean())
