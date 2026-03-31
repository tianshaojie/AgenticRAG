from __future__ import annotations

import logging

from app.core.config import Settings
from app.core.errors import ValidationAppError
from app.reranker.http_provider import HttpRerankerProvider
from app.reranker.interfaces import RerankerProvider
from app.reranker.mock_provider import MockRerankerProvider


def build_reranker_provider(*, settings: Settings) -> RerankerProvider:
    logger = logging.getLogger("app.reranker")

    if not settings.enable_real_reranker_provider:
        logger.info(
            "reranker_provider_selected",
            extra={
                "request_id": "startup",
                "trace_id": "startup",
                "provider_name": "mock",
                "operation": "provider_factory",
                "fallback_used": True,
            },
        )
        return MockRerankerProvider()

    if settings.reranker_provider != "http":
        raise ValidationAppError(
            code="reranker_provider_not_supported",
            message="configured reranker provider is not supported",
            details={"provider": settings.reranker_provider},
        )

    if settings.reranker_api_key is None or not settings.reranker_api_key.get_secret_value().strip():
        raise ValidationAppError(
            code="reranker_api_key_missing",
            message="reranker api key is required when real provider is enabled",
            details={},
        )

    if not settings.reranker_endpoint:
        raise ValidationAppError(
            code="reranker_endpoint_missing",
            message="reranker endpoint is required when real provider is enabled",
            details={},
        )

    logger.info(
        "reranker_provider_selected",
        extra={
            "request_id": "startup",
            "trace_id": "startup",
            "provider_name": "http_reranker",
            "operation": "provider_factory",
            "fallback_used": False,
        },
    )
    return HttpRerankerProvider(
        api_key=settings.reranker_api_key.get_secret_value(),
        base_url=settings.reranker_base_url,
        endpoint=settings.reranker_endpoint,
        app_code=settings.reranker_app_code,
        app_name=settings.reranker_app_name,
        model=settings.reranker_model,
        instruct=settings.reranker_instruct,
        default_top_n=settings.reranker_top_n,
        default_timeout_seconds=settings.reranker_timeout_seconds,
        max_retries=settings.reranker_max_retries,
        backoff_base_ms=settings.provider_backoff_base_ms,
        backoff_max_ms=settings.provider_backoff_max_ms,
    )
