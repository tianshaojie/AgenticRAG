from __future__ import annotations

from app.core.config import Settings
from app.llm.factory import build_llm_provider
from app.services.answer import ThresholdAnswerGenerator


def build_answer_generator(*, settings: Settings) -> ThresholdAnswerGenerator:
    llm_provider = build_llm_provider(settings=settings)
    return ThresholdAnswerGenerator(
        min_citations=settings.evidence_min_citations,
        min_score=settings.evidence_min_score,
        llm_provider=llm_provider,
        llm_model=settings.llm_model,
        llm_temperature=settings.llm_temperature,
        llm_max_tokens=settings.llm_max_tokens,
        llm_timeout_seconds=settings.llm_timeout_seconds,
    )
