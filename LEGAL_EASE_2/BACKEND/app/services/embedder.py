"""Embedding generation using Ollama mxbai-embed-large (1024-dim) with sentence-transformers fallback."""

import asyncio
import json
import os
import logging
from typing import List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Persist _store_dim to disk so it survives server restarts
_STORE_DIM_PATH = os.path.join(settings.CHROMA_PERSIST_DIR, "_store_dim.json")

EMBEDDING_DIM: int = 1024 if settings.EMBEDDING_BACKEND == "ollama" else 384

# Track the *actual* dimension of the last successful embedding call.
# This lets vectorstore detect fallback-vs-primary mismatches at runtime.
_actual_dim: int = EMBEDDING_DIM

# Track the dimension used when documents were stored (persisted to disk)
def _load_store_dim() -> Optional[int]:
    """Load persisted store dimension from disk."""
    try:
        if os.path.exists(_STORE_DIM_PATH):
            with open(_STORE_DIM_PATH, "r") as f:
                data = json.load(f)
                return data.get("dim")
    except Exception:
        pass
    return None

def _save_store_dim(dim: int) -> None:
    """Persist store dimension to disk."""
    try:
        os.makedirs(os.path.dirname(_STORE_DIM_PATH), exist_ok=True)
        with open(_STORE_DIM_PATH, "w") as f:
            json.dump({"dim": dim}, f)
    except Exception as e:
        print(f"[WARN] Could not persist store_dim: {e}")

_store_dim: Optional[int] = _load_store_dim()

# Lazy-loaded sentence-transformers fallback
_st_model = None

# Shared httpx client for Ollama (avoids per-request connection overhead)
_ollama_client: Optional[httpx.AsyncClient] = None


def _get_ollama_client() -> httpx.AsyncClient:
    """Return a reusable async httpx client for Ollama."""
    global _ollama_client
    if _ollama_client is None or _ollama_client.is_closed:
        _ollama_client = httpx.AsyncClient(timeout=300.0)
    return _ollama_client


def get_actual_dim() -> int:
    """Return the dimension of the most recently generated embeddings."""
    return _actual_dim


def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model


# ── Ollama helpers ───────────────────────────────────────────────────

async def _ollama_embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed texts using Ollama /api/embed endpoint with robust error handling.
    
    Includes string cleaning (UTF-8) and granular one-by-one fallback to isolate
    problematic chunks that might cause 400 Bad Request errors.
    """
    embeddings: List[List[float]] = []
    # Smaller batch size for better reliability on consumer hardware
    batch_size = 4  
    client = _get_ollama_client()

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        # Clean strings: ensure valid UTF-8 and strip problematic control characters
        cleaned = []
        for t in batch:
            if not t or not t.strip():
                cleaned.append("empty")
                continue
            # Remove null bytes and ensure valid UTF-8
            safe_text = t.encode("utf-8", "ignore").decode("utf-8").replace("\x00", "")
            cleaned.append(safe_text)

        try:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embed",
                json={"model": settings.OLLAMA_EMBED_MODEL, "input": cleaned, "truncate": True},
                timeout=120.0
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings.extend(data["embeddings"])
        except Exception as batch_error:
            logger.warning(f"Ollama batch embedding failed (Size {len(cleaned)}): {batch_error}. Retrying one-by-one...")
            # Fallback: embed one-by-one to isolate the exact problematic chunk
            for idx, text in enumerate(cleaned):
                try:
                    resp = await client.post(
                        f"{settings.OLLAMA_BASE_URL}/api/embed",
                        json={"model": settings.OLLAMA_EMBED_MODEL, "input": text, "truncate": True},
                        timeout=60.0
                    )
                    if resp.status_code == 400:
                         logger.error(f"❌ Ollama REJECTED chunk (400 Bad Request). Chunk start: {text[:100]}...")
                         # Use a zero-vector as fallback for this specific chunk rather than breaking the whole upload
                         embeddings.append([0.0] * EMBEDDING_DIM)
                         continue
                    
                    resp.raise_for_status()
                    data = resp.json()
                    embeddings.append(data["embeddings"][0])
                except Exception as single_error:
                    logger.error(f"Ollama single embedding failed for text #{idx}: {single_error}")
                    # Final safety: zero-vector so document processing can at least continue
                    embeddings.append([0.0] * EMBEDDING_DIM)

    return embeddings

    return embeddings


async def _ollama_embed_single(text: str) -> List[float]:
    """Embed a single query string via Ollama."""
    client = _get_ollama_client()
    resp = await client.post(
        f"{settings.OLLAMA_BASE_URL}/api/embed",
        json={"model": settings.OLLAMA_EMBED_MODEL, "input": text if text.strip() else "empty", "truncate": True},
    )
    resp.raise_for_status()
    data = resp.json()
    return data["embeddings"][0]


# ── Sentence-Transformers helpers (fallback) ─────────────────────────

def _st_embed_texts(texts: List[str]) -> List[List[float]]:
    model = _get_st_model()
    embs = model.encode(texts, batch_size=64, show_progress_bar=True)
    return embs.tolist()


def _st_embed_query(query: str) -> List[float]:
    model = _get_st_model()
    return model.encode(query).tolist()


# ── Public API (async) ───────────────────────────────────────────────

async def embed_texts(texts: List[str], **kwargs) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.

    Uses Ollama mxbai-embed-large (1024-dim) by default.
    Falls back to sentence-transformers all-MiniLM-L6-v2 (384-dim) if Ollama is unavailable.
    """
    global _actual_dim, _store_dim
    if settings.EMBEDDING_BACKEND == "ollama":
        try:
            logger.info(f"Embedding {len(texts)} texts via Ollama...")
            result = await _ollama_embed_batch(texts)
            _actual_dim = len(result[0]) if result else EMBEDDING_DIM
            if _store_dim is None:
                _store_dim = _actual_dim
                _save_store_dim(_actual_dim)
            logger.info(f"✅ Successfully embedded {len(texts)} texts with Ollama (dim={_actual_dim})")
            return result
        except Exception as e:
            logger.error(f"❌ Ollama embedding completely failed: {type(e).__name__}: {e}")
            raise RuntimeError(f"Ollama failed: {e}") from e
    else:
        try:
            logger.info(f"Embedding {len(texts)} texts via sentence-transformers...")
            result = await asyncio.to_thread(_st_embed_texts, texts)
            _actual_dim = 384
            if _store_dim is None:
                _store_dim = 384
                _save_store_dim(384)
            logger.info(f"✅ Successfully embedded {len(texts)} texts with sentence-transformers (dim=384)")
            return result
        except Exception as e:
            logger.error(f"❌ Sentence-transformers embedding failed: {e}")
            raise


async def embed_query(query: str) -> List[float]:
    """Generate embedding for a single query string.

    Raises RuntimeError if the resulting dimension doesn't match
    the dimension used when documents were stored, preventing
    silent garbage results from dimension mismatches.
    """
    global _actual_dim
    if settings.EMBEDDING_BACKEND == "ollama":
        try:
            logger.info(f"Embedding query via Ollama...")
            result = await _ollama_embed_single(query)
            _actual_dim = len(result)
            # Guard: check dimension matches what was used at storage time
            if _store_dim is not None and _actual_dim != _store_dim:
                logger.warning(f"⚠️  Query dim {_actual_dim} != store dim {_store_dim}. Retrying with Ollama...")
                # One more attempt before giving up
                result = await _ollama_embed_single(query)
                _actual_dim = len(result)
                if _actual_dim != _store_dim:
                    raise RuntimeError(
                        f"Embedding dimension mismatch: query={_actual_dim}, stored={_store_dim}. "
                        f"Ensure Ollama is running with the correct model."
                    )
            logger.info(f"✅ Successfully embedded query with Ollama (dim={_actual_dim})")
            return result
        except RuntimeError:
            raise  # Re-raise dimension mismatch
        except Exception as e:
            logger.warning(f"⚠️  Ollama query embedding failed ({type(e).__name__}: {str(e)[:80]}), falling back to sentence-transformers...")
            try:
                result = await asyncio.to_thread(_st_embed_query, query)
                _actual_dim = 384
                # Guard: if stored with 1024-dim Ollama, don't use 384-dim fallback
                if _store_dim is not None and _store_dim != 384:
                    raise RuntimeError(
                        f"Embedding dimension mismatch: fallback produces 384-dim but documents "
                        f"were stored with {_store_dim}-dim. Ensure Ollama is running."
                    )
                logger.info(f"✅ Successfully embedded query with sentence-transformers (dim=384)")
                return result
            except Exception as fallback_error:
                logger.error(f"❌ Both Ollama and sentence-transformers failed for query: {fallback_error}")
                raise
    else:
        logger.info(f"Embedding query via sentence-transformers...")
        result = await asyncio.to_thread(_st_embed_query, query)
        _actual_dim = 384
        logger.info(f"✅ Successfully embedded query with sentence-transformers (dim=384)")
        return result