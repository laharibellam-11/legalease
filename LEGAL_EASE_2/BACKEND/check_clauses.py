"""Check clause data in MongoDB."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def check():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client["lexichain"]
    async for doc in db["documents"].find({}, {
        "status": 1, "original_name": 1, "clauses": 1,
        "risk_score": 1, "risk_level": 1, "risk_flags": 1,
    }):
        name = doc.get("original_name", "?")
        status = doc.get("status", "?")
        clauses = doc.get("clauses", [])
        risk = doc.get("risk_score")
        risk_lvl = doc.get("risk_level")
        flags = doc.get("risk_flags", [])
        print(f"Doc: {name} | status={status} | clauses={len(clauses)} | risk={risk} ({risk_lvl}) | flags={len(flags)}")
        if clauses:
            for c in clauses[:3]:
                ctype = c.get("type", "?")
                csrc = c.get("source", "?")
                conf = c.get("confidence", 0)
                txt = c.get("text", "")[:100]
                print(f"  clause: type={ctype} src={csrc} conf={conf} text={txt}...")
        else:
            print("  NO CLAUSES STORED!")
    client.close()

asyncio.run(check())
