"""Re-process documents stuck in 'processing' or 'error' state."""
import asyncio
import os

from app.core.config import settings
from app.core.database import connect_db
from app.models.document import LegalDocument
from app.services.ocr import extract_text_from_pdf, get_full_text, get_page_count, preprocess_text
from app.services.chunker import chunk_text
from app.services.embedder import embed_texts
from app.services.vectorstore import add_document_chunks
from app.services.clause_extractor import extract_clauses_hybrid
from app.services.risk_engine import calculate_risk_enhanced


async def reprocess(doc):
    file_path = os.path.join(settings.UPLOAD_DIR, doc.user_id, doc.filename)
    if not os.path.exists(file_path):
        print(f"  File not found: {file_path}")
        doc.status = "error"
        doc.error_message = "Source file not found"
        await doc.save()
        return

    try:
        # Step 1: Extract
        print("  Extracting text...")
        page_texts = extract_text_from_pdf(file_path)
        full_text = preprocess_text(get_full_text(page_texts))
        page_count = get_page_count(file_path)
        doc.page_count = page_count
        doc.extracted_text_preview = full_text[:500]

        # Step 2: Chunk
        print("  Chunking...")
        chunks = chunk_text(text=full_text, page_texts=page_texts, doc_id=str(doc.id))
        doc.total_chunks = len(chunks)
        print(f"  {len(chunks)} chunks created")

        # Step 3: Embed
        print("  Generating embeddings...")
        chunk_texts_list = [c["text"] for c in chunks]
        embeddings = await embed_texts(chunk_texts_list)
        print(f"  {len(embeddings)} embeddings generated")

        # Step 4: Vector store
        print("  Storing vectors...")
        add_document_chunks(user_id=doc.user_id, chunks=chunks, embeddings=embeddings)

        # Step 5: Clause extraction
        print("  Extracting clauses...")
        clauses = await extract_clauses_hybrid(chunks)
        doc.clauses = clauses
        print(f"  {len(clauses)} clauses found")

        # Step 6: Risk scoring
        print("  Calculating risk...")
        risk_result = await calculate_risk_enhanced(clauses)
        doc.risk_score = risk_result["score"]
        doc.risk_level = risk_result["level"]
        doc.risk_flags = risk_result["flags"]
        print(f"  Risk: {risk_result['level']} ({risk_result['score']:.1f}%)")

        doc.status = "ready"
        doc.error_message = None
        await doc.save()
        print("  ✅ Done!")

    except Exception as e:
        doc.status = "error"
        doc.error_message = str(e)[:500]
        await doc.save()
        print(f"  ❌ Error: {e}")


async def main():
    import sys
    await connect_db()

    # --all flag: reprocess ALL documents (useful after clearing chroma_data)
    if "--all" in sys.argv:
        docs = await LegalDocument.find_all().to_list()
    else:
        docs = await LegalDocument.find(
            {"status": {"$in": ["processing", "error", "uploaded"]}}
        ).to_list()

    if not docs:
        print("No documents to reprocess.")
        return

    print(f"Found {len(docs)} document(s) to reprocess.")
    for doc in docs:
        print(f"\nReprocessing: {doc.original_name}")
        await reprocess(doc)


if __name__ == "__main__":
    asyncio.run(main())
