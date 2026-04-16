import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.vectorstore import _get_client
from app.services.embedder import embed_query

async def test():
    # 1. Check MongoDB
    c = AsyncIOMotorClient("mongodb://localhost:27017/lexichain")
    doc = await c.lexichain.documents.find_one({})
    if not doc:
        print("MongoDB is empty!")
        return
        
    user_id = str(doc["user_id"])
    print("User ID:", user_id)
    print("Document ID:", doc["_id"])
    print("Total chunks in Mongo:", doc.get("total_chunks", 0))
    
    # 2. Check ChromaDB
    client = _get_client()
    try:
        col = client.get_collection(f"user_{user_id}_documents")
        print("ChromaDB count:", col.count())
        
        if col.count() > 0:
            peek = col.peek(1)
            print("Chroma embedding dim:", len(peek["embeddings"][0]) if peek["embeddings"] else "N/A")
            
            # 3. Test a query manually
            query = "summarize"
            q_emb = await embed_query(query)
            print("Query embedding dim:", len(q_emb))
            
            res = col.query(query_embeddings=[q_emb], n_results=5)
            distances = res["distances"][0] if res and "distances" in res and res["distances"] else []
            print("Top distances for 'summarize':", distances)
            
    except Exception as e:
        print("Chroma Error:", e)

asyncio.run(test())
