from __future__ import annotations

import json

import httpx
import pytest

from app.core.errors import DependencyAppError, TimeoutAppError
from app.reranker.http_provider import HttpRerankerProvider
from app.reranker.interfaces import RerankRequest, RerankerCandidate


def _request() -> RerankRequest:
    return RerankRequest(
        query="机器学习",
        model="qwen3-reranker-8b",
        top_n=2,
        request_id="req-rerank-1",
        trace_id="trace-rerank-1",
        candidates=[
            RerankerCandidate(candidate_id="c1", document="机器学习"),
            RerankerCandidate(candidate_id="c2", document="banana"),
            RerankerCandidate(candidate_id="c3", document="fruit"),
        ],
    )


@pytest.mark.asyncio
async def test_http_reranker_payload_and_response_mapping() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("Authorization", "")
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            status_code=200,
            json={
                "model": "qwen3-reranker-8b",
                "results": [
                    {"index": 1, "score": 0.99},
                    {"index": 0, "score": 0.91},
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = HttpRerankerProvider(
        api_key="test-key",
        endpoint="https://reranker.example.com/v1/rerank",
        app_code="chatbi_reranker",
        app_name="妙查-重排",
        model="qwen3-reranker-8b",
        instruct="Please rerank the documents based on the query.",
        max_retries=0,
        client=client,
    )

    response = await provider.rerank(request=_request())
    await client.aclose()

    assert captured["url"] == "https://reranker.example.com/v1/rerank"
    assert captured["authorization"] == "Bearer test-key"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["app_code"] == "chatbi_reranker"
    assert payload["app_name"] == "妙查-重排"
    assert payload["query"] == "机器学习"
    assert payload["model"] == "qwen3-reranker-8b"
    assert payload["documents"] == ["机器学习", "banana", "fruit"]
    assert payload["top_n"] == 2

    assert [item.candidate_id for item in response.items] == ["c2", "c1"]
    assert [item.rank for item in response.items] == [1, 2]


@pytest.mark.asyncio
async def test_http_reranker_supports_base_url_plus_path() -> None:
    captured: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            status_code=200,
            json={
                "data": [
                    {"index": 0, "score": 0.95},
                    {"index": 2, "score": 0.86},
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = HttpRerankerProvider(
        api_key="test-key",
        base_url="https://reranker.example.com",
        endpoint="/v1/rerank",
        max_retries=0,
        client=client,
    )

    response = await provider.rerank(request=_request())
    await client.aclose()

    assert captured["url"] == "https://reranker.example.com/v1/rerank"
    assert [item.candidate_id for item in response.items] == ["c1", "c3"]


@pytest.mark.asyncio
async def test_http_reranker_retries_on_upstream_5xx() -> None:
    attempts = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(status_code=502, json={"error": "bad gateway"})
        return httpx.Response(status_code=200, json={"results": [{"index": 0}, {"index": 1}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = HttpRerankerProvider(
        api_key="test-key",
        endpoint="https://reranker.example.com/v1/rerank",
        max_retries=1,
        backoff_base_ms=1,
        backoff_max_ms=1,
        client=client,
    )

    response = await provider.rerank(request=_request())
    await client.aclose()

    assert [item.candidate_id for item in response.items] == ["c1", "c2"]
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_http_reranker_maps_authentication_failure() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(status_code=401, json={"error": "unauthorized"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = HttpRerankerProvider(
        api_key="test-key",
        endpoint="https://reranker.example.com/v1/rerank",
        max_retries=3,
        client=client,
    )

    with pytest.raises(DependencyAppError) as exc_info:
        await provider.rerank(request=_request())
    await client.aclose()

    assert exc_info.value.code == "reranker_authentication_failure"


@pytest.mark.asyncio
async def test_http_reranker_maps_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = HttpRerankerProvider(
        api_key="test-key",
        endpoint="https://reranker.example.com/v1/rerank",
        max_retries=0,
        client=client,
    )

    with pytest.raises(TimeoutAppError) as exc_info:
        await provider.rerank(request=_request())
    await client.aclose()

    assert exc_info.value.code == "reranker_timeout"


@pytest.mark.asyncio
async def test_http_reranker_maps_invalid_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(status_code=200, json={"unexpected": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = HttpRerankerProvider(
        api_key="test-key",
        endpoint="https://reranker.example.com/v1/rerank",
        max_retries=0,
        client=client,
    )

    with pytest.raises(DependencyAppError) as exc_info:
        await provider.rerank(request=_request())
    await client.aclose()

    assert exc_info.value.code == "reranker_invalid_response"


@pytest.mark.asyncio
async def test_http_reranker_maps_partial_result() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(status_code=200, json={"results": [{"index": 2, "score": 0.77}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = HttpRerankerProvider(
        api_key="test-key",
        endpoint="https://reranker.example.com/v1/rerank",
        max_retries=0,
        client=client,
    )

    with pytest.raises(DependencyAppError) as exc_info:
        await provider.rerank(request=_request())
    await client.aclose()

    assert exc_info.value.code == "reranker_partial_result"
