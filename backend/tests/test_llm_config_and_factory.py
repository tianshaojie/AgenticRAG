from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.core.errors import ValidationAppError
from app.llm.factory import build_llm_provider
from app.llm.mock_provider import MockLLMProvider
from app.llm.openai_compatible import OpenAICompatibleLLMProvider


def test_settings_load_llm_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("RAG_LLM_API_KEY", "dummy-key")
    monkeypatch.setenv("RAG_LLM_ENDPOINT", "https://agent.cnht.com.cn/v1/chat/completions")
    monkeypatch.setenv("RAG_LLM_MODEL", "demo-model")
    monkeypatch.setenv("RAG_ENABLE_REAL_LLM_PROVIDER", "true")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.llm_provider == "openai_compatible"
    assert settings.llm_api_key is not None
    assert settings.llm_api_key.get_secret_value() == "dummy-key"
    assert settings.llm_endpoint == "https://agent.cnht.com.cn/v1/chat/completions"
    assert settings.llm_model == "demo-model"
    assert settings.enable_real_llm_provider is True

    monkeypatch.delenv("RAG_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_LLM_API_KEY", raising=False)
    monkeypatch.delenv("RAG_LLM_ENDPOINT", raising=False)
    monkeypatch.delenv("RAG_LLM_MODEL", raising=False)
    monkeypatch.delenv("RAG_ENABLE_REAL_LLM_PROVIDER", raising=False)
    get_settings.cache_clear()


def test_factory_returns_mock_when_real_provider_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_ENABLE_REAL_LLM_PROVIDER", "false")
    get_settings.cache_clear()
    settings = get_settings()

    provider = build_llm_provider(settings=settings)
    assert isinstance(provider, MockLLMProvider)

    monkeypatch.delenv("RAG_ENABLE_REAL_LLM_PROVIDER", raising=False)
    get_settings.cache_clear()


def test_factory_requires_api_key_when_real_provider_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_ENABLE_REAL_LLM_PROVIDER", "true")
    monkeypatch.setenv("RAG_LLM_PROVIDER", "openai_compatible")
    monkeypatch.delenv("RAG_LLM_API_KEY", raising=False)
    get_settings.cache_clear()
    settings = get_settings()

    with pytest.raises(ValidationAppError) as exc_info:
        _ = build_llm_provider(settings=settings)

    assert exc_info.value.code == "llm_api_key_missing"

    monkeypatch.delenv("RAG_ENABLE_REAL_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_LLM_PROVIDER", raising=False)
    get_settings.cache_clear()


def test_factory_returns_openai_provider_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_ENABLE_REAL_LLM_PROVIDER", "true")
    monkeypatch.setenv("RAG_LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("RAG_LLM_API_KEY", "dummy-key")
    monkeypatch.setenv("RAG_LLM_ENDPOINT", "https://agent.cnht.com.cn/v1/chat/completions")
    get_settings.cache_clear()
    settings = get_settings()

    provider = build_llm_provider(settings=settings)
    assert isinstance(provider, OpenAICompatibleLLMProvider)

    monkeypatch.delenv("RAG_ENABLE_REAL_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_LLM_API_KEY", raising=False)
    monkeypatch.delenv("RAG_LLM_ENDPOINT", raising=False)
    get_settings.cache_clear()
