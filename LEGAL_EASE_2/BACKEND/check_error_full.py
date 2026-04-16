import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    c = AsyncIOMotorClient("mongodb://localhost:27017/lexichain")
    docs = await c.lexichain.documents.find({"status": "error"}).to_list(10)
    for doc in docs:
        print("-" * 20)
        print("FILENAME:", doc.get("original_name"))
        print("ERROR_MSG:", doc.get("error_message"))
        print("PROGRESS:", doc.get("processing_progress"))
        print("STEP:", doc.get("processing_step"))

if __name__ == "__main__":
    asyncio.run(check())
