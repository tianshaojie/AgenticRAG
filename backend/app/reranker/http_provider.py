from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import urljoin

import httpx

from app.core.errors import DependencyAppError, TimeoutAppError, UnavailableAppError, ValidationAppError
from app.reranker.interfaces import (
    RerankRequest,
    RerankResponse,
    RerankedItem,
    RerankerProvider,
)


class HttpRerankerProvider(RerankerProvider):
    """HTTP adapter for external reranker providers."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        base_url: str | None = None,
        app_code: str = "chatbi_reranker",
        app_name: str = "妙查-重排",
        model: str = "qwen3-reranker-8b",
        instruct: str = "Please rerank the documents based on the query.",
        default_top_n: int = 5,
        default_timeout_seconds: int = 8,
        max_retries: int = 2,
        backoff_base_ms: int = 100,
        backoff_max_ms: int = 1000,
        logger: logging.Logger | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._endpoint = endpoint.strip()
        self._base_url = base_url.strip() if base_url else None
        self._app_code = app_code
        self._app_name = app_name
        self._model = model
        self._instruct = instruct
        self._default_top_n = max(default_top_n, 1)
        self._default_timeout_seconds = default_timeout_seconds
        self._max_retries = max(max_retries, 0)
        self._backoff_base_ms = max(backoff_base_ms, 1)
        self._backoff_max_ms = max(backoff_max_ms, self._backoff_base_ms)
        self._logger = logger or logging.getLogger("app.reranker.http")
        self._client = client

    def _resolved_url(self) -> str:
        if self._endpoint.startswith("http://") or self._endpoint.startswith("https://"):
            return self._endpoint

        if not self._base_url:
            raise ValidationAppError(
                code="reranker_endpoint_invalid",
                message="reranker endpoint must be absolute URL or configured with reranker_base_url",
                details={"endpoint": self._endpoint},
            )

        base = self._base_url if self._base_url.endswith("/") else f"{self._base_url}/"
        return urljoin(base, self._endpoint.lstrip("/"))

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ValidationAppError(
                code="reranker_api_key_missing",
                message="reranker api key is required when real provider is enabled",
                details={},
            )
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, request: RerankRequest) -> dict[str, object]:
        top_n = min(max(request.top_n, 1), len(request.candidates)) if request.candidates else 0
        if top_n <= 0:
            raise ValidationAppError(
                code="reranker_candidates_empty",
                message="reranker candidates must not be empty",
                details={},
            )

        return {
            "app_code": self._app_code,
            "app_name": self._app_name,
            "query": request.query,
            "model": request.model or self._model,
            "documents": [candidate.document for candidate in request.candidates],
            "instruct": self._instruct,
            "top_n": top_n,
        }

    def _map_http_error(self, *, status_code: int) -> DependencyAppError | UnavailableAppError:
        if status_code in {401, 403}:
            return DependencyAppError(
                code="reranker_authentication_failure",
                message="reranker provider authentication failed",
                details={"status_code": status_code},
                retryable=False,
            )
        if status_code == 429:
            return UnavailableAppError(
                code="reranker_rate_limited",
                message="reranker provider rate limited",
                details={"status_code": status_code},
            )
        if status_code >= 500:
            return UnavailableAppError(
                code="reranker_upstream_server_error",
                message="reranker upstream server error",
                details={"status_code": status_code},
            )
        return DependencyAppError(
            code="reranker_provider_http_error",
            message="reranker provider returned non-success response",
            details={"status_code": status_code},
            retryable=False,
        )

    @staticmethod
    def _extract_rows(payload: dict) -> list:
        for key in ("results", "data", "output", "result"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return rows
        raise DependencyAppError(
            code="reranker_invalid_response",
            message="reranker response missing result list",
            details={},
            retryable=False,
        )

    @staticmethod
    def _coerce_float(value: object) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _resolve_candidate_index(
        *,
        row: object,
        candidates: list,
        by_id: dict[str, int],
        by_document: dict[str, int],
    ) -> int:
        if isinstance(row, str):
            if row in by_document:
                return by_document[row]
            raise DependencyAppError(
                code="reranker_invalid_response",
                message="reranker row text does not match any input candidate",
                details={},
                retryable=False,
            )

        if not isinstance(row, dict):
            raise DependencyAppError(
                code="reranker_invalid_response",
                message="reranker row is not an object",
                details={},
                retryable=False,
            )

        for index_key in ("index", "document_index", "doc_index", "idx", "position"):
            value = row.get(index_key)
            if isinstance(value, int) and 0 <= value < len(candidates):
                return value

        candidate_id = row.get("candidate_id") or row.get("id")
        if isinstance(candidate_id, str) and candidate_id in by_id:
            return by_id[candidate_id]

        for text_key in ("document", "text", "content"):
            value = row.get(text_key)
            if isinstance(value, str) and value in by_document:
                return by_document[value]

        raise DependencyAppError(
            code="reranker_invalid_response",
            message="reranker row cannot be mapped to input candidate",
            details={},
            retryable=False,
        )

    def _parse_response(self, *, payload: dict, request: RerankRequest) -> RerankResponse:
        rows = self._extract_rows(payload)
        if not rows:
            raise DependencyAppError(
                code="reranker_empty_result",
                message="reranker returned empty result",
                details={},
                retryable=False,
            )

        by_id = {candidate.candidate_id: idx for idx, candidate in enumerate(request.candidates)}
        by_document = {candidate.document: idx for idx, candidate in enumerate(request.candidates)}

        items: list[RerankedItem] = []
        seen: set[str] = set()
        for position, row in enumerate(rows, start=1):
            original_index = self._resolve_candidate_index(
                row=row,
                candidates=request.candidates,
                by_id=by_id,
                by_document=by_document,
            )
            candidate = request.candidates[original_index]
            if candidate.candidate_id in seen:
                continue
            seen.add(candidate.candidate_id)

            rank = position
            score = None
            if isinstance(row, dict):
                rank_value = row.get("rank")
                if isinstance(rank_value, int) and rank_value > 0:
                    rank = rank_value
                score = self._coerce_float(
                    row.get("score")
                    if "score" in row
                    else row.get("relevance_score", row.get("similarity"))
                )

            items.append(
                RerankedItem(
                    candidate_id=candidate.candidate_id,
                    original_index=original_index,
                    rank=rank,
                    score=score,
                )
            )

        if not items:
            raise DependencyAppError(
                code="reranker_empty_result",
                message="reranker returned no mappable items",
                details={},
                retryable=False,
            )

        expected = min(max(request.top_n, 1), len(request.candidates))
        if len(items) < expected:
            raise DependencyAppError(
                code="reranker_partial_result",
                message="reranker returned partial result set",
                details={"expected": expected, "actual": len(items)},
                retryable=False,
            )

        items.sort(key=lambda item: item.rank)
        return RerankResponse(
            items=items[:expected],
            model=payload.get("model") if isinstance(payload.get("model"), str) else None,
            metadata={"id": payload.get("id"), "usage": payload.get("usage")},
        )

    async def _post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> httpx.Response:
        if self._client is not None:
            return await self._client.post(url, json=payload, headers=headers, timeout=timeout_seconds)

        async with httpx.AsyncClient() as client:
            return await client.post(url, json=payload, headers=headers, timeout=timeout_seconds)

    async def rerank(self, *, request: RerankRequest) -> RerankResponse:
        url = self._resolved_url()
        payload = self._payload(request)
        headers = self._headers()
        timeout_seconds = request.timeout_seconds or float(self._default_timeout_seconds)
        max_attempts = self._max_retries + 1

        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            started = time.perf_counter()
            try:
                response = await self._post_json(
                    url=url,
                    payload=payload,
                    headers=headers,
                    timeout_seconds=timeout_seconds,
                )
                if response.status_code >= 400:
                    raise self._map_http_error(status_code=response.status_code)

                body = response.json()
                if not isinstance(body, dict):
                    raise DependencyAppError(
                        code="reranker_invalid_response",
                        message="reranker response is not a json object",
                        details={},
                        retryable=False,
                    )

                result = self._parse_response(payload=body, request=request)
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                self._logger.info(
                    "reranker_call_succeeded",
                    extra={
                        "request_id": request.request_id,
                        "trace_id": request.trace_id,
                        "provider_name": "http_reranker",
                        "operation": "rerank",
                        "attempt": attempt,
                        "latency_ms": latency_ms,
                        "fallback_used": False,
                    },
                )
                return result
            except httpx.TimeoutException:
                error = TimeoutAppError(
                    code="reranker_timeout",
                    message="reranker provider request timed out",
                    details={"timeout_seconds": timeout_seconds},
                )
            except httpx.TransportError:
                error = UnavailableAppError(
                    code="reranker_provider_unavailable",
                    message="reranker provider transport unavailable",
                    details={},
                )
            except (DependencyAppError, UnavailableAppError, TimeoutAppError) as exc:
                error = exc
            except Exception:
                error = DependencyAppError(
                    code="reranker_provider_unavailable",
                    message="reranker provider request failed unexpectedly",
                    details={},
                )

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            self._logger.warning(
                "reranker_call_failed",
                extra={
                    "request_id": request.request_id,
                    "trace_id": request.trace_id,
                    "provider_name": "http_reranker",
                    "operation": "rerank",
                    "attempt": attempt,
                    "latency_ms": latency_ms,
                    "fallback_used": False,
                    "error_code": error.code,
                },
            )
            if attempt >= max_attempts or not error.retryable:
                raise error

            backoff_ms = min(self._backoff_base_ms * (2 ** (attempt - 1)), self._backoff_max_ms)
            await asyncio.sleep(backoff_ms / 1000)

        raise UnavailableAppError(
            code="reranker_retry_exhausted",
            message="reranker provider retries exhausted",
            details={"max_retries": self._max_retries},
        )
