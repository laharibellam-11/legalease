import asyncio
from app.core.database import connect_db
from app.models.document import LegalDocument

async def main():
    await connect_db()
    docs = await LegalDocument.find(LegalDocument.status == "error").to_list()
    for d in docs:
        print(f"ID: {d.id}")
        print(f"Name: {d.original_name}")
        print(f"Error: {d.error_message}")
        print(f"Chunks: {d.total_chunks}")
        print("---")

asyncio.run(main())
