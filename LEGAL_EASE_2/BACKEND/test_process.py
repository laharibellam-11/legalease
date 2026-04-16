import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.embedder import embed_texts

async def test():
    # Grab 2 real chunks from DB if we can, else mock
    c = AsyncIOMotorClient("mongodb://localhost:27017/lexichain")
    doc = await c.lexichain.documents.find_one({})
    if not doc:
        print("No doc to re-process.")
        return
        
    clauses = doc.get("clauses", [])
    texts = [c.get("text", "mock text") for c in clauses]
    if not texts:
        texts = ["This is mock text chunk " + str(i) for i in range(20)]
        
    print(f"Testing batch embed with {len(texts)} chunks of avg len {sum(len(t) for t in texts)/len(texts)}")
    
    try:
        res = await embed_texts(texts)
        print("Embed success!", len(res))
    except Exception as e:
        print("Embed failed! Error:", type(e).__name__, str(e))

asyncio.run(test())
