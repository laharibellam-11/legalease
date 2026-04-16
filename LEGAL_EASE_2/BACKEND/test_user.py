import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test():
    c = AsyncIOMotorClient("mongodb://localhost:27017/lexichain")
    user = await c.lexichain.users.find_one({"email": "lona@gmail.com"})
    print("User ID:", user["_id"])
    
    docs = await c.lexichain.documents.find({"user_id": str(user["_id"])}).to_list(length=100)
    print("Doc matching:", [(d.get("status"), d.get("total_chunks")) for d in docs])

asyncio.run(test())
