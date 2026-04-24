from typing import Literal
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)


class RetrievedTicket(BaseModel):
    text: str   # customer tweet: what was searched against
    company_reply: str | None = None # brand's response: given to the LLM as resolution context
    similarity_score: float
    brand: str | None = None


class LLMAnswer(BaseModel):
    text: str
    latency_ms: float
    cost_usd: float
    accuracy_score: float | None = None  # 0-1, RAG only; None for non-RAG


class PriorityPrediction(BaseModel):
    label: Literal["urgent", "normal"]
    confidence: float
    latency_ms: float
    cost_usd: float


class QueryResponse(BaseModel):
    query: str
    rag_answer: LLMAnswer
    non_rag_answer: LLMAnswer
    retrieved_tickets: list[RetrievedTicket]
    ml_priority: PriorityPrediction
    llm_priority: PriorityPrediction
