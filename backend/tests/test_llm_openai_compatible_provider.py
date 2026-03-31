from __future__ import annotations

import httpx
import pytest

from app.core.errors import DependencyAppError, TimeoutAppError
from app.llm.interfaces import LLMCompletionRequest, LLMMessage
from app.llm.openai_compatible import OpenAICompatibleLLMProvider


@pytest.mark.asyncio
async def test_openai_compatible_provider_accepts_full_endpoint_url() -> None:
    captured: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("Authorization", "")
        return httpx.Response(
            status_code=200,
            json={
                "id": "resp-1",
                "model": "demo-model",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "answer text"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleLLMProvider(
        api_key="test-key",
        endpoint="https://agent.cnht.com.cn/v1/chat/completions",
        max_retries=0,
        client=client,
    )

    response = await provider.chat_completion(
        request=LLMCompletionRequest(
            model="demo-model",
            messages=[LLMMessage(role="user", content="hello")],
            request_id="req-1",
            trace_id="trace-1",
        )
    )
    await client.aclose()

    assert response.text == "answer text"
    assert captured["url"] == "https://agent.cnht.com.cn/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_openai_compatible_provider_accepts_base_url_plus_path() -> None:
    captured: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            status_code=200,
            json={
                "model": "demo-model",
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleLLMProvider(
        api_key="test-key",
        base_url="https://agent.cnht.com.cn",
        endpoint="/v1/chat/completions",
        max_retries=0,
        client=client,
    )
    response = await provider.chat_completion(
        request=LLMCompletionRequest(
            model="demo-model",
            messages=[LLMMessage(role="user", content="hello")],
        )
    )
    await client.aclose()

    assert response.text == "ok"
    assert captured["url"] == "https://agent.cnht.com.cn/v1/chat/completions"


@pytest.mark.asyncio
async def test_openai_compatible_provider_retries_on_upstream_5xx() -> None:
    state = {"attempt": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        state["attempt"] += 1
        if state["attempt"] == 1:
            return httpx.Response(status_code=502, json={"error": "upstream down"})
        return httpx.Response(
            status_code=200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "recovered"}}],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleLLMProvider(
        api_key="test-key",
        endpoint="https://agent.cnht.com.cn/v1/chat/completions",
        max_retries=1,
        backoff_base_ms=1,
        backoff_max_ms=1,
        client=client,
    )

    response = await provider.chat_completion(
        request=LLMCompletionRequest(
            model="demo-model",
            messages=[LLMMessage(role="user", content="hello")],
        )
    )
    await client.aclose()

    assert response.text == "recovered"
    assert state["attempt"] == 2


@pytest.mark.asyncio
async def test_openai_compatible_provider_maps_authentication_failure() -> None:
    state = {"attempt": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        state["attempt"] += 1
        return httpx.Response(status_code=401, json={"error": "unauthorized"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleLLMProvider(
        api_key="test-key",
        endpoint="https://agent.cnht.com.cn/v1/chat/completions",
        max_retries=3,
        client=client,
    )

    with pytest.raises(DependencyAppError) as exc_info:
        await provider.chat_completion(
            request=LLMCompletionRequest(
                model="demo-model",
                messages=[LLMMessage(role="user", content="hello")],
            )
        )
    await client.aclose()

    assert exc_info.value.code == "llm_authentication_failure"
    assert state["attempt"] == 1


@pytest.mark.asyncio
async def test_openai_compatible_provider_maps_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleLLMProvider(
        api_key="test-key",
        endpoint="https://agent.cnht.com.cn/v1/chat/completions",
        max_retries=0,
        client=client,
    )

    with pytest.raises(TimeoutAppError) as exc_info:
        await provider.chat_completion(
            request=LLMCompletionRequest(
                model="demo-model",
                messages=[LLMMessage(role="user", content="hello")],
                timeout_seconds=0.01,
            )
        )
    await client.aclose()

    assert exc_info.value.code == "llm_timeout"


@pytest.mark.asyncio
async def test_openai_compatible_provider_maps_invalid_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(status_code=200, json={"choices": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleLLMProvider(
        api_key="test-key",
        endpoint="https://agent.cnht.com.cn/v1/chat/completions",
        max_retries=0,
        client=client,
    )

    with pytest.raises(DependencyAppError) as exc_info:
        await provider.chat_completion(
            request=LLMCompletionRequest(
                model="demo-model",
                messages=[LLMMessage(role="user", content="hello")],
            )
        )
    await client.aclose()

    assert exc_info.value.code == "llm_invalid_response"
