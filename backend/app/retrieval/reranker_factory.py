from __future__ import annotations

from app.core.config import Settings
from app.reranker.factory import build_reranker_provider
from app.retrieval.reranker import ProviderBackedReranker


def build_reranker(*, settings: Settings) -> ProviderBackedReranker:
    provider = build_reranker_provider(settings=settings)
    return ProviderBackedReranker(
        provider=provider,
        enable_reranking=settings.enable_reranking,
        model=settings.reranker_model,
        timeout_seconds=float(settings.reranker_timeout_seconds),
        default_top_n=settings.reranker_top_n,
    )
