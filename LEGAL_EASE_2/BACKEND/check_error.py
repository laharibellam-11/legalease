import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    c = AsyncIOMotorClient("mongodb://localhost:27017/lexichain")
    doc = await c.lexichain.documents.find_one({"status": "error"})
    if doc:
        print("ERROR_MSG:", doc.get("error_message"))
        print("FILENAME:", doc.get("original_name"))
    else:
        print("NO ERROR DOCS FOUND")

if __name__ == "__main__":
    asyncio.run(check())
