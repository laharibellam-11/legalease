from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import cast

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.types import ExceptionHandler

from app.core.config import settings
from app.core.database import connect_db, close_db
from app.core.limiter import limiter
from app.api import auth, documents, analysis, comparison, admin
from app.services.rag import warmup_ollama

# ──────────────── Lifespan ────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    # Pre-load Ollama model into memory so first LLM call is fast
    await warmup_ollama()
    yield
    await close_db()


# ──────────────── App Instance ────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Legal Document Analyzer using RAG and LLMs",
    version="1.0.0",
    lifespan=lifespan,
)

# ──────────────── Middleware ────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(ExceptionHandler, _rate_limit_exceeded_handler))

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────── Routes ────────────────
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(analysis.router)
app.include_router(comparison.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
