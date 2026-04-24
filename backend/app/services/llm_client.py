import json
import logging
import time
from functools import lru_cache
from typing import Any, Literal

import openai
from fastapi import HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.schemas import LLMAnswer, PriorityPrediction, RetrievedTicket

logger = logging.getLogger(__name__)

# Pricing constants
# GPT-4o (USD per token)
_OAI_PRICE_INPUT        = 2.50  / 1_000_000
_OAI_PRICE_OUTPUT       = 10.00 / 1_000_000
_OAI_PRICE_CACHED_INPUT = 1.25  / 1_000_000

# Gemini 2.5 Flash (USD per token — verify at ai.google.dev/pricing)
_GEM_PRICE_INPUT  = 0.075 / 1_000_000
_GEM_PRICE_OUTPUT = 0.30  / 1_000_000

# Shared prompt
_ANSWER_SYSTEM_PROMPT = (
    "You are a helpful customer support assistant. "
    "Answer questions concisely and specifically. "
    "When similar past cases are provided, use them to ground your answer."
    "If no relevant information can be found in the provided cases, answer based on your general knowledge and provide sources if possible."
)

_RAG_SYSTEM_PROMPT = (
    _ANSWER_SYSTEM_PROMPT
    + " After answering, rate accuracy_score (0.0-1.0): how well your answer is grounded "
    "in the provided cases (1.0 = fully from context, 0.0 = not at all)."
)

# Internal structured output schemas
class _AnswerOutput(BaseModel):
    answer: str

class _RagAnswerOutput(BaseModel):
    answer: str
    accuracy_score: float  # 0-1: how well the answer is grounded in the provided cases

class _PriorityOutput(BaseModel):
    label: Literal["urgent", "normal"]
    confidence: float


# Client factories
@lru_cache(maxsize=1)
def _get_openai() -> openai.OpenAI:
    return openai.OpenAI(api_key=get_settings().openai_api_key)


@lru_cache(maxsize=1)
def _get_gemini() -> Any:
    import google.generativeai as genai
    genai.configure(api_key=get_settings().gemini_api_key)  # type: ignore[attr-defined]
    return genai


# Cost helpers
def _oai_cost(usage: openai.types.CompletionUsage) -> float:
    cached = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0
    regular = usage.prompt_tokens - cached
    return round(
        regular * _OAI_PRICE_INPUT
        + cached * _OAI_PRICE_CACHED_INPUT
        + usage.completion_tokens * _OAI_PRICE_OUTPUT,
        8,
    )


def _gem_cost(usage) -> float:
    return round(
        usage.prompt_token_count       * _GEM_PRICE_INPUT
        + usage.candidates_token_count * _GEM_PRICE_OUTPUT,
        8,
    )


# Context formatter (shared)
def _format_context(tickets: list[RetrievedTicket]) -> str:
    parts = []
    for i, t in enumerate(tickets, 1):
        block = f"--- Case {i} (similarity: {t.similarity_score:.2f}) ---\nCustomer: {t.text}"
        if t.company_reply:
            block += f"\nSupport: {t.company_reply}"
        parts.append(block)
    return "\n\n".join(parts)


# Private OpenAI functions
def _openai_rag_answer(query: str, tickets: list[RetrievedTicket]) -> LLMAnswer:
    context = _format_context(tickets)
    user_msg = f"Similar past cases:\n\n{context}\n\n---\nQuestion: {query}"
    t0 = time.perf_counter()
    try:
        resp = _get_openai().beta.chat.completions.parse(
            model=get_settings().openai_model,
            max_tokens=512,
            messages=[
                {"role": "system", "content": _RAG_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format=_RagAnswerOutput,
        )
    except openai.RateLimitError as exc:
        raise HTTPException(status_code=429, detail="OpenAI rate limit") from exc
    except openai.APIError as exc:
        raise HTTPException(status_code=502, detail="OpenAI API error") from exc
    parsed = resp.choices[0].message.parsed  # type: ignore[union-attr]
    return LLMAnswer(
        text=parsed.answer,
        latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        cost_usd=_oai_cost(resp.usage),  # type: ignore[arg-type]
        accuracy_score=round(parsed.accuracy_score, 2),
    )


def _openai_non_rag_answer(query: str) -> LLMAnswer:
    t0 = time.perf_counter()
    try:
        resp = _get_openai().beta.chat.completions.parse(
            model=get_settings().openai_model,
            max_tokens=512,
            messages=[
                {"role": "system", "content": _ANSWER_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            response_format=_AnswerOutput,
        )
    except openai.RateLimitError as exc:
        raise HTTPException(status_code=429, detail="OpenAI rate limit") from exc
    except openai.APIError as exc:
        raise HTTPException(status_code=502, detail="OpenAI API error") from exc
    return LLMAnswer(
        text=resp.choices[0].message.parsed.answer,  # type: ignore[union-attr]
        latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        cost_usd=_oai_cost(resp.usage),  # type: ignore[arg-type]
    )


def _openai_priority(text: str) -> PriorityPrediction:
    t0 = time.perf_counter()
    try:
        resp = _get_openai().beta.chat.completions.parse(
            model=get_settings().openai_model,
            max_tokens=128,
            messages=[
                {"role": "system", "content": "Classify customer support tickets as urgent or normal."},
                {"role": "user", "content": f"Classify this ticket:\n\n{text}"},
            ],
            response_format=_PriorityOutput,
        )
    except openai.RateLimitError as exc:
        raise HTTPException(status_code=429, detail="OpenAI rate limit") from exc
    except openai.APIError as exc:
        raise HTTPException(status_code=502, detail="OpenAI API error") from exc
    result = resp.choices[0].message.parsed  # type: ignore[union-attr]
    return PriorityPrediction(
        label=result.label,  # type: ignore[union-attr]
        confidence=round(result.confidence, 4),  # type: ignore[union-attr]
        latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        cost_usd=_oai_cost(resp.usage),  # type: ignore[arg-type]
    )


# Private Gemini functions 
def _gemini_answer(system: str, user_msg: str) -> tuple[str, object, float]:
    # Shared helper: returns (answer_text, usage_metadata, latency_ms)
    genai = _get_gemini()
    prompt = f"{system}\n\n{user_msg}\n\nRespond with JSON: {{\"answer\": \"your response\"}}"
    t0 = time.perf_counter()
    try:
        model = genai.GenerativeModel(get_settings().gemini_model)
        resp = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json"),
        )
    except Exception as exc:
        logger.exception("Gemini API error")
        raise HTTPException(status_code=502, detail="Gemini API error") from exc
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    answer = json.loads(resp.text)["answer"]
    return answer, resp.usage_metadata, latency_ms


def _gemini_rag_answer(query: str, tickets: list[RetrievedTicket]) -> LLMAnswer:
    context = _format_context(tickets)
    user_msg = f"Similar past cases:\n\n{context}\n\n---\nQuestion: {query}"
    genai = _get_gemini()
    prompt = (
        f"{_RAG_SYSTEM_PROMPT}\n\n{user_msg}\n\n"
        'Respond with JSON: {"answer": "your response", "accuracy_score": 0.0}'
    )
    t0 = time.perf_counter()
    try:
        model = genai.GenerativeModel(get_settings().gemini_model)
        resp = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json"),
        )
    except Exception as exc:
        logger.exception("Gemini API error")
        raise HTTPException(status_code=502, detail="Gemini API error") from exc
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    data = json.loads(resp.text)
    return LLMAnswer(
        text=data["answer"],
        latency_ms=latency_ms,
        cost_usd=_gem_cost(resp.usage_metadata),
        accuracy_score=round(float(data.get("accuracy_score", 0.0)), 2),
    )


def _gemini_non_rag_answer(query: str) -> LLMAnswer:
    answer, usage, latency_ms = _gemini_answer(_ANSWER_SYSTEM_PROMPT, query)
    return LLMAnswer(text=answer, latency_ms=latency_ms, cost_usd=_gem_cost(usage))


def _gemini_priority(text: str) -> PriorityPrediction:
    genai = _get_gemini()
    prompt = (
        "Classify this customer support ticket as urgent or normal.\n"
        'Respond with JSON only: {"label": "urgent" or "normal", "confidence": 0.0-1.0}\n\n'
        f"Ticket: {text}"
    )
    t0 = time.perf_counter()
    try:
        model = genai.GenerativeModel(get_settings().gemini_model)
        resp = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json"),
        )
    except Exception as exc:
        logger.exception("Gemini API error in priority")
        raise HTTPException(status_code=502, detail="Gemini API error") from exc
    result = json.loads(resp.text)
    return PriorityPrediction(
        label=result["label"],
        confidence=round(float(result["confidence"]), 4),
        latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        cost_usd=_gem_cost(resp.usage_metadata),
    )


# Public interface with fallback
def _should_fallback(exc: HTTPException) -> bool:
    return exc.status_code in (429, 502) and bool(get_settings().gemini_api_key)


def generate_rag_answer(query: str, tickets: list[RetrievedTicket]) -> LLMAnswer:
    try:
        return _openai_rag_answer(query, tickets)
    except HTTPException as exc:
        if _should_fallback(exc):
            logger.warning("OpenAI failed (%d) — falling back to Gemini", exc.status_code)
            return _gemini_rag_answer(query, tickets)
        raise


def generate_non_rag_answer(query: str) -> LLMAnswer:
    try:
        return _openai_non_rag_answer(query)
    except HTTPException as exc:
        if _should_fallback(exc):
            logger.warning("OpenAI failed (%d) — falling back to Gemini", exc.status_code)
            return _gemini_non_rag_answer(query)
        raise


def predict_priority_llm(text: str) -> PriorityPrediction:
    try:
        return _openai_priority(text)
    except HTTPException as exc:
        if _should_fallback(exc):
            logger.warning("OpenAI failed (%d) — falling back to Gemini", exc.status_code)
            return _gemini_priority(text)
        raise