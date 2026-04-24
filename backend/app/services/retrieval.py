import logging
from functools import lru_cache

import chromadb
from fastapi import HTTPException

from app.config import get_settings
from app.schemas import RetrievedTicket
from app.utils.embeddings import get_embedding_function

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_collection():
    #Open the persisted ChromaDB collection once per process
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    ef = get_embedding_function()
    try:
        collection = client.get_collection(
            name=settings.chroma_collection_name,
            embedding_function=ef,  # type: ignore[arg-type]
        )
        logger.info(
            "ChromaDB collection '%s' opened (%d documents)",
            settings.chroma_collection_name,
            collection.count(),
        )
        return collection
    except Exception as exc:
        # The collection doesn't exist yet: ingest.py hasn't been run
        raise RuntimeError(
            f"ChromaDB collection '{settings.chroma_collection_name}' not found. "
            "Run 'python -m app.utils.ingest' to populate it."
        ) from exc


def retrieve(query: str, top_k: int | None = None) -> list[RetrievedTicket]:
    # Return the top-k most similar tickets for a query.

    settings = get_settings()
    k = top_k if top_k is not None else settings.top_k_results

    try:
        collection = _get_collection()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    results = collection.query(query_texts=[query], n_results=k)

    docs = results["documents"][0]       # type: ignore[index]
    metas = results["metadatas"][0]      # type: ignore[index]
    distances = results["distances"][0]  # type: ignore[index]

    tickets = []
    for doc, meta, distance in zip(docs, metas, distances):
        # cosine distance in [0, 1] for unit-norm embeddings
        similarity = round(1.0 - float(distance), 4)
        reply = str(meta.get("company_reply", ""))
        tickets.append(
            RetrievedTicket(
                text=str(doc),
                company_reply=reply if reply else None,
                similarity_score=max(similarity, 0.0),  # clamp against float noise
                brand=str(meta["brand"]) if "brand" in meta else None,
            )
        )

    return tickets