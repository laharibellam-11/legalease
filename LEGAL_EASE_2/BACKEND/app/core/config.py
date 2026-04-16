"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "LegalEase"
    DEBUG: bool = False

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017/legalease"

    # Google Gemini
    GEMINI_API_KEY: str = ""

    # JWT
    JWT_SECRET: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    # Embedding (Ollama)
    EMBEDDING_BACKEND: str = "ollama"  # "ollama" or "sentence-transformers"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBED_MODEL: str = "mxbai-embed-large"
    OLLAMA_EMBED_DIMENSIONS: int = 1024

    # Ollama Generation (local LLM fallback)
    OLLAMA_GEN_MODEL: str = "qwen2.5:7b"
    OLLAMA_GEN_ENABLED: bool = True

    # Legal-BERT
    LEGAL_BERT_MODEL: str = "nlpaueb/legal-bert-base-uncased"
    LEGAL_BERT_ENABLED: bool = True

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
