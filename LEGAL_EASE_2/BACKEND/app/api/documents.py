"""Document upload, listing, deletion, and processing routes."""

import os
import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, status

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.document import LegalDocument
from app.models.user import User
from app.schemas.schemas import DocumentListResponse, DocumentResponse
from app.services.ocr import extract_text_from_pdf, get_full_text, get_page_count, preprocess_text
from app.services.chunker import chunk_text
from app.services.embedder import embed_texts
from app.services.vectorstore import add_document_chunks, delete_document_chunks
from app.services.clause_extractor import extract_clauses_hybrid
from app.services.risk_engine import calculate_risk_enhanced

router = APIRouter(prefix="/api/documents", tags=["Documents"])

ALLOWED_TYPES = ["application/pdf"]
MAX_FILES_PER_UPLOAD = 3


async def _process_document(doc_id: str, file_path: str, user_id: str):
    """Background task: extract text, chunk, embed, analyze, and store."""
    doc = await LegalDocument.get(doc_id)
    if not doc:
        return

    try:
        # Step 1: Extract text (10%)
        doc.processing_step = "Extracting text from PDF"
        doc.processing_progress = 5
        await doc.save()

        page_texts = extract_text_from_pdf(file_path)
        full_text = get_full_text(page_texts)
        full_text = preprocess_text(full_text)
        page_count = get_page_count(file_path)

        doc.page_count = page_count
        doc.extracted_text_preview = full_text[:500]
        doc.processing_progress = 15
        doc.processing_step = "Text extraction complete"
        await doc.save()

        # Step 2: Chunk the text (25%)
        doc.processing_step = "Splitting into chunks"
        doc.processing_progress = 20
        await doc.save()

        chunks = chunk_text(
            text=full_text,
            page_texts=page_texts,
            doc_id=str(doc.id),
        )
        doc.total_chunks = len(chunks)
        print(f"[DOC] [Processor] Created {len(chunks)} chunks for doc {doc_id}")
        doc.processing_progress = 30
        doc.processing_step = f"Created {len(chunks)} chunks"
        await doc.save()

        # Step 3: Generate embeddings (50%)
        doc.processing_step = "Generating embeddings"
        doc.processing_progress = 35
        await doc.save()

        chunk_texts = [c["text"] for c in chunks]
        embeddings = await embed_texts(chunk_texts)

        doc.processing_progress = 55
        doc.processing_step = f"Embedded {len(embeddings)} chunks"
        await doc.save()

        # Step 4: Store in vector DB (60%)
        doc.processing_step = "Storing vectors"
        doc.processing_progress = 58
        await doc.save()

        add_document_chunks(
            user_id=user_id,
            chunks=chunks,
            embeddings=embeddings,
        )

        doc.processing_progress = 65
        doc.processing_step = "Vectors stored"
        await doc.save()

        # Step 5: Extract clauses (65-90%)
        doc.processing_step = "Analyzing clauses (AI)"
        doc.processing_progress = 68
        await doc.save()

        async def clause_progress(pct):
            # Map 0-100 LLM progress to 68-90 overall progress
            mapped = 68 + int(pct * 0.22)
            doc.processing_progress = min(mapped, 90)
            doc.processing_step = f"Analyzing clauses ({pct}%)"
            await doc.save()

        clauses = await extract_clauses_hybrid(chunks, on_progress=clause_progress)
        doc.clauses = clauses

        # Step 6: Calculate risk (95%)
        doc.processing_step = "Calculating risk score"
        doc.processing_progress = 92
        await doc.save()

        risk_result = await calculate_risk_enhanced(clauses, doc.extracted_text_preview or "")
        doc.contract_type = risk_result.get("contract_type")
        doc.risk_score = risk_result["score"]
        doc.risk_level = risk_result["level"]
        doc.risk_flags = risk_result["risks"]
        doc.risk_results = risk_result

        # Mark as ready (100%)
        doc.status = "ready"
        doc.processing_step = "Complete"
        doc.processing_progress = 100
        await doc.save()

    except Exception as e:
        doc.status = "error"
        doc.error_message = str(e)[:500]
        await doc.save()
        print(f"Document processing error ({doc_id}): {e}")


@router.post("/upload", response_model=List[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    user: User = Depends(get_current_user),
):
    """Upload 1–3 PDF documents for analysis."""
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_FILES_PER_UPLOAD} files per upload",
        )

    created_docs = []

    for file in files:
        # Validate file type
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type: {file.filename}. Only PDF files are allowed.",
            )

        # Validate file size
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.",
            )

        # Save file
        user_dir = os.path.join(settings.UPLOAD_DIR, str(user.id))
        os.makedirs(user_dir, exist_ok=True)

        original_name: str = str(file.filename) if file.filename else "document.pdf"
        file_ext = os.path.splitext(original_name)[1] or ".pdf"
        stored_name = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(user_dir, stored_name)

        with open(file_path, "wb") as f:
            f.write(content)

        # Create document record
        doc = LegalDocument(
            user_id=str(user.id),
            filename=stored_name,
            original_name=original_name,
            file_size=len(content),
            status="processing",
        )
        await doc.insert()

        # Schedule background processing
        background_tasks.add_task(_process_document, str(doc.id), file_path, str(user.id))

        created_docs.append(DocumentResponse(
            id=str(doc.id),
            original_name=doc.original_name,
            file_size=doc.file_size,
            page_count=doc.page_count,
            upload_date=doc.upload_date,
            status=doc.status,
            processing_step=doc.processing_step,
            processing_progress=doc.processing_progress,
            total_chunks=doc.total_chunks,
        ))

    return created_docs


@router.get("/", response_model=DocumentListResponse)
async def list_documents(user: User = Depends(get_current_user)):
    """List all documents for the current user."""
    docs = await LegalDocument.find(LegalDocument.user_id == str(user.id)).to_list()
    doc_responses = [
        DocumentResponse(
            id=str(d.id),
            original_name=d.original_name,
            file_size=d.file_size,
            page_count=d.page_count,
            upload_date=d.upload_date,
            status=d.status,
            processing_step=d.processing_step,
            processing_progress=d.processing_progress,
            extracted_text_preview=d.extracted_text_preview,
            total_chunks=d.total_chunks,
            risk_score=d.risk_score,
            risk_level=d.risk_level,
            clauses=d.clauses,
            risk_flags=d.risk_flags,
        )
        for d in docs
    ]
    return DocumentListResponse(documents=doc_responses, total=len(doc_responses))


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, user: User = Depends(get_current_user)):
    """Get a single document's details."""
    doc = await LegalDocument.get(doc_id)
    if not doc or doc.user_id != str(user.id):
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=str(doc.id),
        original_name=doc.original_name,
        file_size=doc.file_size,
        page_count=doc.page_count,
        upload_date=doc.upload_date,
        status=doc.status,
        processing_step=doc.processing_step,
        processing_progress=doc.processing_progress,
        extracted_text_preview=doc.extracted_text_preview,
        total_chunks=doc.total_chunks,
        risk_score=doc.risk_score,
        risk_level=doc.risk_level,
        clauses=doc.clauses,
        risk_flags=doc.risk_flags,
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: str, user: User = Depends(get_current_user)):
    """Delete a document and its vector data."""
    doc = await LegalDocument.get(doc_id)
    if not doc or doc.user_id != str(user.id):
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from vector store
    try:
        delete_document_chunks(str(user.id), doc_id)
    except Exception:
        pass

    # Remove file
    file_path = os.path.join(settings.UPLOAD_DIR, str(user.id), doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Remove DB record
    await doc.delete()
