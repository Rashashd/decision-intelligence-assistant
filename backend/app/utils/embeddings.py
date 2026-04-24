import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_function():
    # Return the ChromaDB embedding function for the configured provider
    # Both ingest.py and retrieval.py call this so they always use the same function and thus the same embeddings.
    
    from app.config import get_settings
    settings = get_settings()

    if settings.embedding_provider not in ("openai", "gemini"):
        logger.warning(
            "Unrecognised EMBEDDING_PROVIDER '%s' — falling back to 'openai'.",
            settings.embedding_provider,
        )

    if settings.embedding_provider == "gemini":
        from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction
        return GoogleGenerativeAiEmbeddingFunction(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_embedding_model,
        )

    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
    return OpenAIEmbeddingFunction(
        api_key=settings.openai_api_key,
        model_name=settings.openai_embedding_model,
    )