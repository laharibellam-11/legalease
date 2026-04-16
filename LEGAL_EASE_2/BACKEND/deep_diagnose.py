import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import chromadb
import os
from app.core.config import settings

async def diagnose():
    client = AsyncIOMotorClient("mongodb://localhost:27017/lexichain")
    
    print("--- MONGODB USERS ---")
    users = await client.lexichain.users.find({}).to_list(100)
    for u in users:
        print(f"Name: {u.get('full_name')} | Email: {u.get('email')} | ID: {str(u['_id'])}")
        
    print("\n--- MONGODB DOCUMENTS ---")
    docs = await client.lexichain.documents.find({}).to_list(100)
    for d in docs:
        print(f"File: {d.get('original_name')} | Status: {d.get('status')} | UserID: {d.get('user_id')} | ID: {str(d['_id'])}")
        
    print("\n--- CHROMADB COLLECTIONS ---")
    persist_dir = settings.CHROMA_PERSIST_DIR
    chroma = chromadb.PersistentClient(path=persist_dir)
    cols = chroma.list_collections()
    for col in cols:
        print(f"Collection: {col.name} | Count: {col.count()}")

if __name__ == "__main__":
    asyncio.run(diagnose())
