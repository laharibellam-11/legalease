"""ChromaDB vector store for document chunk storage and retrieval."""

import os
from typing import Any, Dict, List, Optional, cast

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.services.embedder import EMBEDDING_DIM


# Singleton ChromaDB client — avoids expensive re-init on every request
_chroma_client: Any = None


def _get_client() -> Any:
    """Get or create a persistent ChromaDB client (cached singleton)."""
    global _chroma_client
    if _chroma_client is None:
        persist_dir = settings.CHROMA_PERSIST_DIR
        os.makedirs(persist_dir, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=persist_dir)
    return _chroma_client


def get_or_create_collection(user_id: str) -> Any:
    """Get or create a ChromaDB collection for a user.

    Automatically recreates the collection if the embedding dimension
    has changed (e.g. migrating from 384-dim to 1024-dim).
    """
    client = _get_client()
    collection_name = f"user_{user_id}_documents"

    # Try to get existing collection and check dimension compatibility
    try:
        existing = client.get_collection(name=collection_name)
        # Peek at one record to check its embedding dimension
        peek = existing.peek(limit=1)
        embeddings = peek.get("embeddings") if peek else None
        if embeddings is not None and len(embeddings) > 0:
            old_dim = len(embeddings[0])
            if old_dim != EMBEDDING_DIM:
                print(f"[WARN] Dimension Mismatch: Collection {old_dim} but system {EMBEDDING_DIM}. Wiping stale collection.")
                client.delete_collection(name=collection_name)
            else:
                print(f"[OK] Collection '{collection_name}' verified ({old_dim}-dim, {existing.count()} items)")
    except Exception as e:
        print(f"[INFO] Creating fresh collection for user: {user_id}")

    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def add_document_chunks(
    user_id: str,
    chunks: List[dict],
    embeddings: List[List[float]],
) -> None:
    """
    Store document chunks with embeddings in ChromaDB.
    
    Args:
        user_id: Owner's user ID
        chunks: List of chunk dicts with keys: chunk_id, text, doc_id, page_number, clause_heading
        embeddings: Corresponding embedding vectors
    """
    collection = get_or_create_collection(user_id)

    ids = [chunk["chunk_id"] for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    metadatas: Any = [
        {
            "doc_id": chunk["doc_id"],
            "page_number": chunk["page_number"],
            "clause_heading": chunk["clause_heading"],
            "token_count": chunk.get("token_count", 0),
        }
        for chunk in chunks
    ]

    print(f"[LOAD] [Chroma] Adding {len(ids)} chunks for doc {chunks[0]['doc_id'] if chunks else 'N/A'}...")
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=cast(Any, embeddings),
        metadatas=metadatas,
    )
    print(f"[OK] [Chroma] Successfully saved {len(ids)} chunks. New total count: {collection.count()}")


def query_similar_chunks(
    user_id: str,
    query_embedding: List[float],
    top_k: int = 5,
    doc_ids: Optional[List[str]] = None,
    max_distance: float = 1.3,
) -> List[dict]:
    """
    Search for top-K similar chunks in a user's collection.
    
    Args:
        user_id: Owner's user ID
        query_embedding: Query vector
        top_k: Number of results to return
        doc_ids: Optional filter to specific documents
        max_distance: Maximum cosine distance threshold (0=identical, 2=opposite).
                      Chunks further than this are filtered out as irrelevant.
    
    Returns:
        List of {chunk_id, text, metadata, distance}
    """
    collection = get_or_create_collection(user_id)

    where_filter: Any = None
    if doc_ids:
        if len(doc_ids) == 1:
            where_filter = {"doc_id": doc_ids[0]}
        else:
            where_filter = {"doc_id": {"$in": doc_ids}}

    # Retrieve more than needed so we can filter by distance
    fetch_k = min(top_k * 2, top_k + 10)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=fetch_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results and results["ids"] and results["ids"][0]:
        docs = results["documents"] or []
        metas = results["metadatas"] or []
        dists = results["distances"] or []
        for i, chunk_id in enumerate(results["ids"][0]):
            distance = dists[0][i] if dists else 0.0
            # Filter out chunks that are too far away (irrelevant)
            if distance > max_distance:
                continue
            chunks.append({
                "chunk_id": chunk_id,
                "text": docs[0][i] if docs else "",
                "metadata": metas[0][i] if metas else {},
                "distance": distance,
            })

    # Return only top_k after filtering
    return chunks[:top_k]


def delete_document_chunks(user_id: str, doc_id: str) -> None:
    """Delete all chunks belonging to a specific document."""
    collection = get_or_create_collection(user_id)
    # Get all chunk IDs for this doc
    results = collection.get(where={"doc_id": doc_id}, include=[])
    if results and results["ids"]:
        collection.delete(ids=results["ids"])


def get_collection_stats(user_id: str) -> dict:
    """Get stats about a user's vector collection."""
    collection = get_or_create_collection(user_id)
    return {"count": collection.count()}
