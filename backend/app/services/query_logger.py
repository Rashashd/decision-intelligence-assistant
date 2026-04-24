import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.schemas import QueryResponse

logger = logging.getLogger(__name__)


def log_query(response: QueryResponse) -> None:
    # JSONL (one JSON object per line) is append-only and easy to parse later. One file per day so logs don't grow unbounded.

    settings = get_settings()
    log_dir = Path(settings.log_dir)

    try:
        log_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc)
        log_file = log_dir / f"queries_{now.strftime('%Y-%m-%d')}.jsonl"

        record = {
            "timestamp": now.isoformat(),
            "query": response.query,
            "retrieved_tickets": [
                {
                    "text": t.text,
                    "similarity_score": t.similarity_score,
                    "brand": t.brand,
                    "has_company_reply": t.company_reply is not None,
                }
                for t in response.retrieved_tickets
            ],
            "rag_answer": {
                "text": response.rag_answer.text,
                "latency_ms": response.rag_answer.latency_ms,
                "cost_usd": response.rag_answer.cost_usd,
            },
            "non_rag_answer": {
                "text": response.non_rag_answer.text,
                "latency_ms": response.non_rag_answer.latency_ms,
                "cost_usd": response.non_rag_answer.cost_usd,
            },
            "ml_priority": {
                "label": response.ml_priority.label,
                "confidence": response.ml_priority.confidence,
                "latency_ms": response.ml_priority.latency_ms,
                "cost_usd": response.ml_priority.cost_usd,
            },
            "llm_priority": {
                "label": response.llm_priority.label,
                "confidence": response.llm_priority.confidence,
                "latency_ms": response.llm_priority.latency_ms,
                "cost_usd": response.llm_priority.cost_usd,
            },
        }

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    except Exception:
        logger.exception("Failed to write query log — continuing without logging")