import json
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # OpenAI: primary LLM and (optional) embedding provider
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # Gemini: fallback LLM and (optional) embedding provider
    # Leave empty if you don't want Gemini fallback
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    # Which provider to use for embeddings: "openai" or "gemini"
    # Must be the same value at ingestion time and at runtime, changing it after ingestion requires re-running ingest.py to rebuild the vector store.
    embedding_provider: str = "openai"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "support_tickets"

    # RAG
    top_k_results: int = 5

    # Logging
    log_dir: str = "./logs"

    # ML model artifact (saved by the notebook)
    model_path: str = "./models/priority_classifier.joblib"

    # CORS: kept as str so pydantic-settings doesn't attempt JSON-parsing.
    # Accepts comma-separated ("a,b") or JSON array ("[\"a\",\"b\"]") or empty.
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    def get_cors_origins(self) -> list[str]:
        v = self.cors_origins.strip()
        if not v:
            return ["http://localhost:3000", "http://localhost:5173"]
        if v.startswith("["):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return [o.strip() for o in v.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
