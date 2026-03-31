from __future__ import annotations

import pytest

from app.api import routes as api_routes
from app.core.config import get_settings
from app.core.errors import ValidationAppError
from app.llm.interfaces import LLMCompletionResponse


@pytest.fixture(autouse=True)
def reset_runtime_provider_settings():
    settings = get_settings()
    snapshot = {
        "llm_api_key": settings.llm_api_key,
        "reranker_api_key": settings.reranker_api_key,
        "enable_real_llm_provider": settings.enable_real_llm_provider,
        "enable_real_reranker_provider": settings.enable_real_reranker_provider,
        "enable_reranking": settings.enable_reranking,
    }
    yield
    settings.llm_api_key = snapshot["llm_api_key"]
    settings.reranker_api_key = snapshot["reranker_api_key"]
    settings.enable_real_llm_provider = snapshot["enable_real_llm_provider"]
    settings.enable_real_reranker_provider = snapshot["enable_real_reranker_provider"]
    settings.enable_reranking = snapshot["enable_reranking"]


@pytest.mark.integration
def test_get_provider_settings_masks_secrets(client) -> None:
    response = client.get("/settings/providers")
    assert response.status_code == 200
    payload = response.json()

    assert payload["llm"]["name"] == "llm"
    assert payload["reranker"]["name"] == "reranker"
    assert payload["llm"]["has_api_key"] in {True, False}
    assert payload["reranker"]["has_api_key"] in {True, False}
    assert "note" in payload


@pytest.mark.integration
def test_update_provider_settings_accepts_independent_keys(client) -> None:
    response = client.put(
        "/settings/providers",
        json={
            "llm_api_key": "sk-test-12345678",
            "reranker_api_key": "rk-test-abcdef12",
            "llm_endpoint": "https://agent.cnht.com.cn/v1/chat/completions",
            "llm_model": "gpt-4o-mini",
            "reranker_endpoint": "https://reranker.example.com/v1/rerank",
            "reranker_model": "qwen3-reranker-8b",
            "enable_real_llm_provider": True,
            "enable_real_reranker_provider": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm"]["enabled"] is True
    assert payload["reranker"]["enabled"] is True
    assert payload["llm"]["has_api_key"] is True
    assert payload["reranker"]["has_api_key"] is True
    assert payload["llm"]["api_key_last4"].endswith("5678")
    assert payload["reranker"]["api_key_last4"].endswith("ef12")
    assert payload["llm"]["endpoint"] == "https://agent.cnht.com.cn/v1/chat/completions"
    assert payload["reranker"]["endpoint"] == "https://reranker.example.com/v1/rerank"


@pytest.mark.integration
def test_provider_check_returns_degraded_when_real_providers_disabled(client) -> None:
    update_resp = client.put(
        "/settings/providers",
        json={
            "enable_real_llm_provider": False,
            "enable_real_reranker_provider": False,
        },
    )
    assert update_resp.status_code == 200

    response = client.post("/settings/providers/check", json={"target": "all"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    checks_by_provider = {item["provider"]: item for item in payload["checks"]}
    assert checks_by_provider["llm"]["status"] == "degraded"
    assert checks_by_provider["reranker"]["status"] == "degraded"


@pytest.mark.integration
def test_provider_check_uses_factories_and_reports_failures(client, monkeypatch: pytest.MonkeyPatch) -> None:
    update_resp = client.put(
        "/settings/providers",
        json={
            "llm_api_key": "sk-test-12345678",
            "reranker_api_key": "rk-test-abcdef12",
            "enable_real_llm_provider": True,
            "enable_real_reranker_provider": True,
        },
    )
    assert update_resp.status_code == 200

    class _FakeLLMProvider:
        async def chat_completion(self, *, request):
            _ = request
            return LLMCompletionResponse(text="ok", model="fake-llm")

    class _BrokenRerankerProvider:
        async def rerank(self, *, request):
            _ = request
            raise ValidationAppError(
                code="reranker_authentication_failure",
                message="auth failed",
            )

    monkeypatch.setattr(api_routes, "build_llm_provider", lambda settings: _FakeLLMProvider())
    monkeypatch.setattr(api_routes, "build_reranker_provider", lambda settings: _BrokenRerankerProvider())

    response = client.post("/settings/providers/check", json={"target": "all"})
    assert response.status_code == 200
    payload = response.json()
    checks_by_provider = {item["provider"]: item for item in payload["checks"]}

    assert checks_by_provider["llm"]["status"] == "ok"
    assert checks_by_provider["llm"]["detail"].startswith("llm provider reachable")
    assert checks_by_provider["reranker"]["status"] == "failed"
    assert "reranker_authentication_failure" in checks_by_provider["reranker"]["detail"]
