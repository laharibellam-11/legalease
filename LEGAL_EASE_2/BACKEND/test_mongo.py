import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test():
    c = AsyncIOMotorClient("mongodb://localhost:27017/lexichain")
    doc = await c.lexichain.documents.find_one({})
    if doc:
        print("TOTAL CHUNKS:", doc.get("total_chunks", -1))
        print("STATUS:", doc.get("status", ""))
        print("ERROR:", doc.get("error_message", ""))
    else:
        print("NO DOCUMENTS IN DB")

asyncio.run(test())
