from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.core.errors import ValidationAppError
from app.reranker.factory import build_reranker_provider
from app.reranker.http_provider import HttpRerankerProvider
from app.reranker.mock_provider import MockRerankerProvider


def test_settings_load_reranker_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_RERANKER_PROVIDER", "http")
    monkeypatch.setenv("RAG_RERANKER_API_KEY", "dummy-reranker-key")
    monkeypatch.setenv("RAG_RERANKER_ENDPOINT", "https://reranker.example.com/v1/rerank")
    monkeypatch.setenv("RAG_RERANKER_MODEL", "qwen3-reranker-8b")
    monkeypatch.setenv("RAG_ENABLE_REAL_RERANKER_PROVIDER", "true")
    monkeypatch.setenv("RAG_ENABLE_RERANKING", "true")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.reranker_provider == "http"
    assert settings.reranker_api_key is not None
    assert settings.reranker_api_key.get_secret_value() == "dummy-reranker-key"
    assert settings.reranker_endpoint == "https://reranker.example.com/v1/rerank"
    assert settings.reranker_model == "qwen3-reranker-8b"
    assert settings.enable_real_reranker_provider is True
    assert settings.enable_reranking is True

    monkeypatch.delenv("RAG_RERANKER_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_RERANKER_API_KEY", raising=False)
    monkeypatch.delenv("RAG_RERANKER_ENDPOINT", raising=False)
    monkeypatch.delenv("RAG_RERANKER_MODEL", raising=False)
    monkeypatch.delenv("RAG_ENABLE_REAL_RERANKER_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_ENABLE_RERANKING", raising=False)
    get_settings.cache_clear()


def test_reranker_factory_returns_mock_when_real_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_ENABLE_REAL_RERANKER_PROVIDER", "false")
    get_settings.cache_clear()
    settings = get_settings()

    provider = build_reranker_provider(settings=settings)
    assert isinstance(provider, MockRerankerProvider)

    monkeypatch.delenv("RAG_ENABLE_REAL_RERANKER_PROVIDER", raising=False)
    get_settings.cache_clear()


def test_reranker_factory_requires_api_key_when_real_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_ENABLE_REAL_RERANKER_PROVIDER", "true")
    monkeypatch.setenv("RAG_RERANKER_PROVIDER", "http")
    monkeypatch.setenv("RAG_RERANKER_ENDPOINT", "https://reranker.example.com/v1/rerank")
    monkeypatch.delenv("RAG_RERANKER_API_KEY", raising=False)
    get_settings.cache_clear()
    settings = get_settings()

    with pytest.raises(ValidationAppError) as exc_info:
        _ = build_reranker_provider(settings=settings)

    assert exc_info.value.code == "reranker_api_key_missing"

    monkeypatch.delenv("RAG_ENABLE_REAL_RERANKER_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_RERANKER_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_RERANKER_ENDPOINT", raising=False)
    get_settings.cache_clear()


def test_reranker_factory_requires_endpoint_when_real_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_ENABLE_REAL_RERANKER_PROVIDER", "true")
    monkeypatch.setenv("RAG_RERANKER_PROVIDER", "http")
    monkeypatch.setenv("RAG_RERANKER_API_KEY", "dummy-reranker-key")
    monkeypatch.delenv("RAG_RERANKER_ENDPOINT", raising=False)
    get_settings.cache_clear()
    settings = get_settings()

    with pytest.raises(ValidationAppError) as exc_info:
        _ = build_reranker_provider(settings=settings)

    assert exc_info.value.code == "reranker_endpoint_missing"

    monkeypatch.delenv("RAG_ENABLE_REAL_RERANKER_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_RERANKER_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_RERANKER_API_KEY", raising=False)
    get_settings.cache_clear()


def test_reranker_factory_returns_http_provider_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_ENABLE_REAL_RERANKER_PROVIDER", "true")
    monkeypatch.setenv("RAG_RERANKER_PROVIDER", "http")
    monkeypatch.setenv("RAG_RERANKER_API_KEY", "dummy-reranker-key")
    monkeypatch.setenv("RAG_RERANKER_ENDPOINT", "https://reranker.example.com/v1/rerank")
    get_settings.cache_clear()
    settings = get_settings()

    provider = build_reranker_provider(settings=settings)
    assert isinstance(provider, HttpRerankerProvider)

    monkeypatch.delenv("RAG_ENABLE_REAL_RERANKER_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_RERANKER_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_RERANKER_API_KEY", raising=False)
    monkeypatch.delenv("RAG_RERANKER_ENDPOINT", raising=False)
    get_settings.cache_clear()
