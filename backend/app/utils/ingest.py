# Populate ChromaDB with tweet embeddings.
# Run once before starting the backend (or when the vector store is empty):

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd
import chromadb

from app.config import get_settings
from app.utils.embeddings import get_embedding_function

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SAMPLE_PER_BRAND = 7000
BATCH_SIZE = 256


def _find_default_data_path() -> Path:
    # Locate inbound_processed.pkl in both Docker and local dev environments
    env_path = os.getenv("PROCESSED_DATA_PATH")
    if env_path:
        return Path(env_path)

    docker_path = Path("/app/data/inbound_processed.pkl")
    if docker_path.exists():
        return docker_path

    return Path(__file__).parents[3] / "data" / "inbound_processed.pkl"


def _collection_exists() -> bool:
    # Return True if the collection already has documents
    settings = get_settings()
    try:
        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        collection = client.get_collection(settings.chroma_collection_name)
        count = collection.count()
        if count > 0:
            logger.info(
                "Collection '%s' already has %d documents — skipping ingest.",
                settings.chroma_collection_name, count,
            )
            return True
    except Exception:
        pass
    return False


def ingest(data_path: Path) -> None:
    settings = get_settings()

    logger.info("Loading processed data from %s", data_path)
    df = pd.read_pickle(data_path)
    logger.info("Loaded %d rows", len(df))

    sampled = pd.concat(
        [g.sample(min(len(g), SAMPLE_PER_BRAND), random_state=42) for _, g in df.groupby("brand", sort=False)],
        ignore_index=True,
    )
    sampled = sampled[sampled["text"].str.strip().str.len() > 0].copy()
    logger.info("Sampled %d tweets across %d brands", len(sampled), sampled["brand"].nunique())

    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

    try:
        client.delete_collection(settings.chroma_collection_name)
        logger.info("Deleted existing collection '%s'", settings.chroma_collection_name)
    except Exception:
        pass

    collection = client.create_collection(
        name=settings.chroma_collection_name,
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )

    texts = sampled["text"].tolist()
    ids = [str(i) for i in range(len(texts))]
    metadatas = [
        {
            "brand": str(row["brand"]),
            "priority": int(row["priority"]),
            "tweet_id": str(row["tweet_id"]),
            "company_reply": str(row.get("company_reply", "")),
        }
        for _, row in sampled.iterrows()
    ]

    total = len(texts)
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        collection.add(
            documents=texts[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end],
        )
        logger.info("Ingested %d / %d", end, total)

    logger.info(
        "Done. Collection '%s' has %d documents.",
        settings.chroma_collection_name,
        collection.count(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest tweets into ChromaDB")
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument(
        "--skip-if-exists",
        action="store_true",
        help="Do nothing if the collection already has documents (used by Docker init container)",
    )
    args = parser.parse_args()

    if args.skip_if_exists and _collection_exists():
        return

    data_path = args.data or _find_default_data_path()

    if not data_path.exists():
        logger.error("Data file not found: %s", data_path)
        logger.error("Run the notebook first to generate inbound_processed.pkl")
        sys.exit(1)

    ingest(data_path)


if __name__ == "__main__":
    main()