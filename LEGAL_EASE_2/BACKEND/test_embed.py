import asyncio
from app.services.embedder import embed_texts
async def test():
    try:
        res = await embed_texts(["hello world"])
        print("Dim:", len(res[0]))
    except Exception as e:
        print("ERROR:", e)
asyncio.run(test())
