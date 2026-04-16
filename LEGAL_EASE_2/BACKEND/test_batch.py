import asyncio
from app.services.embedder import _ollama_embed_batch

async def test():
    texts = ["This is a test document block."] * 20
    try:
        res = await _ollama_embed_batch(texts)
        print("Success, got", len(res), "embeddings of dim", len(res[0]))
    except Exception as e:
        print("Error:", repr(e))

asyncio.run(test())
