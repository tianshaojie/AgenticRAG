from __future__ import annotations

import logging

from app.core.config import Settings
from app.core.errors import ValidationAppError
from app.llm.interfaces import LLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.openai_compatible import OpenAICompatibleLLMProvider


def build_llm_provider(*, settings: Settings) -> LLMProvider:
    logger = logging.getLogger("app.llm")

    if not settings.enable_real_llm_provider:
        logger.info(
            "llm_provider_selected",
            extra={
                "request_id": "startup",
                "trace_id": "startup",
                "provider_name": "mock",
                "operation": "provider_factory",
                "fallback_used": True,
            },
        )
        return MockLLMProvider()

    if settings.llm_provider != "openai_compatible":
        raise ValidationAppError(
            code="llm_provider_not_supported",
            message="configured llm provider is not supported",
            details={"provider": settings.llm_provider},
        )

    if settings.llm_api_key is None or not settings.llm_api_key.get_secret_value().strip():
        raise ValidationAppError(
            code="llm_api_key_missing",
            message="llm api key is required when real llm provider is enabled",
            details={},
        )

    logger.info(
        "llm_provider_selected",
        extra={
            "request_id": "startup",
            "trace_id": "startup",
            "provider_name": "openai_compatible",
            "operation": "provider_factory",
            "fallback_used": False,
        },
    )
    return OpenAICompatibleLLMProvider(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        endpoint=settings.llm_endpoint,
        default_timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        backoff_base_ms=settings.provider_backoff_base_ms,
        backoff_max_ms=settings.provider_backoff_max_ms,
    )
