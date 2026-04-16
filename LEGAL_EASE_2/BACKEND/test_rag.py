import asyncio
from app.services.rag import rag_query
from app.services.vectorstore import _get_client
from app.core.database import connect_db
from motor.motor_asyncio import AsyncIOMotorClient

async def test():
    c = AsyncIOMotorClient("mongodb://localhost:27017/lexichain")
    doc = await c.lexichain.documents.find_one({})
    if not doc:
        print("NO DOC")
        return
        
    doc_id = str(doc["_id"])
    user_id = doc["user_id"]
    
    # check chroma directly
    client = _get_client()
    col = client.get_collection(f"user_{user_id}_documents")
    print(f"Chroma doc count: {col.count()}")
    
    # check rag
    res = await rag_query(
        user_id=user_id,
        query="What is the scope of the agreement?",
        doc_ids=[doc_id]
    )
    print("Answer:", res["answer"])
    print("Chunks found:", len(res["retrieved_chunks"]))

asyncio.run(test())
