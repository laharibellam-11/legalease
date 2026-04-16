import asyncio
from app.services.vectorstore import add_document_chunks, query_similar_chunks, _get_client
from app.services.embedder import embed_texts

async def test_roundtrip():
    user_id = "test_user_unique_123"
    text = "This is a secret code: BANANA."
    chunks = [{"chunk_id": "c1", "text": text, "doc_id": "d1", "page_number": 1, "clause_heading": "Test"}]
    
    print("Embedding...")
    embeddings = await embed_texts([text])
    
    print("Adding to Chroma...")
    add_document_chunks(user_id, chunks, embeddings)
    
    # Check count immediately
    client = _get_client()
    col = client.get_collection(f"user_{user_id}_documents")
    print(f"Count immediately after add: {col.count()}")
    
    print("Querying...")
    search_emb = await embed_texts(["secret code"])
    results = query_similar_chunks(user_id, search_emb[0], top_k=1)
    
    if results:
        print("SUCCESS! Found:", results[0]["text"])
    else:
        print("FAILURE: No results found.")
        
    # Cleanup
    client.delete_collection(f"user_{user_id}_documents")

if __name__ == "__main__":
    asyncio.run(test_roundtrip())
