import logging

from fastapi import APIRouter

from app.schemas import QueryRequest, QueryResponse
from app.services import llm_client, ml_predictor, query_logger, retrieval

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def run_query(request: QueryRequest) -> QueryResponse:
    logger.info("Query received: %.80s", request.query)

    # Step 1: retrieve similar tickets (needed by RAG answer)
    tickets = retrieval.retrieve(request.query)

    # Steps 2–5 run sequentially; each result feeds into the response
    rag_answer     = llm_client.generate_rag_answer(request.query, tickets)
    non_rag_answer = llm_client.generate_non_rag_answer(request.query)
    ml_priority    = ml_predictor.predict_priority(request.query)
    llm_priority   = llm_client.predict_priority_llm(request.query)

    logger.info(
        "Query done — RAG: %.0fms $%.6f | non-RAG: %.0fms $%.6f | ML: %.0fms | LLM-priority: %.0fms $%.6f",
        rag_answer.latency_ms,     rag_answer.cost_usd,
        non_rag_answer.latency_ms, non_rag_answer.cost_usd,
        ml_priority.latency_ms,
        llm_priority.latency_ms,   llm_priority.cost_usd,
    )

    response = QueryResponse(
        query=request.query,
        rag_answer=rag_answer,
        non_rag_answer=non_rag_answer,
        retrieved_tickets=tickets,
        ml_priority=ml_priority,
        llm_priority=llm_priority,
    )

    query_logger.log_query(response)
    return response
