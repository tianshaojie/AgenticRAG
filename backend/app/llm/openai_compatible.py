from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import urljoin

import httpx

from app.core.errors import DependencyAppError, TimeoutAppError, UnavailableAppError, ValidationAppError
from app.llm.interfaces import LLMCompletionRequest, LLMCompletionResponse, LLMProvider


class OpenAICompatibleLLMProvider(LLMProvider):
    """OpenAI Chat Completions compatible provider adapter."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        base_url: str | None = None,
        default_timeout_seconds: int = 15,
        max_retries: int = 2,
        backoff_base_ms: int = 100,
        backoff_max_ms: int = 1000,
        logger: logging.Logger | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._endpoint = endpoint.strip()
        self._base_url = base_url.strip() if base_url else None
        self._default_timeout_seconds = default_timeout_seconds
        self._max_retries = max(max_retries, 0)
        self._backoff_base_ms = max(backoff_base_ms, 1)
        self._backoff_max_ms = max(backoff_max_ms, self._backoff_base_ms)
        self._logger = logger or logging.getLogger("app.llm.openai_compatible")
        self._client = client

    def _resolved_url(self) -> str:
        if self._endpoint.startswith("http://") or self._endpoint.startswith("https://"):
            return self._endpoint

        if not self._base_url:
            raise ValidationAppError(
                code="llm_endpoint_invalid",
                message="llm endpoint must be absolute URL or configured with llm_base_url",
                details={"endpoint": self._endpoint},
            )

        base = self._base_url if self._base_url.endswith("/") else f"{self._base_url}/"
        return urljoin(base, self._endpoint.lstrip("/"))

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ValidationAppError(
                code="llm_api_key_missing",
                message="llm api key is required when real provider is enabled",
                details={},
            )
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, request: LLMCompletionRequest) -> dict:
        payload: dict[str, object] = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload

    def _map_http_error(self, *, status_code: int) -> DependencyAppError | UnavailableAppError:
        if status_code in {401, 403}:
            return DependencyAppError(
                code="llm_authentication_failure",
                message="llm provider authentication failed",
                details={"status_code": status_code},
                retryable=False,
            )
        if status_code == 429:
            return UnavailableAppError(
                code="llm_rate_limited",
                message="llm provider rate limited",
                details={"status_code": status_code},
            )
        if status_code >= 500:
            return UnavailableAppError(
                code="llm_upstream_server_error",
                message="llm upstream server error",
                details={"status_code": status_code},
            )
        return DependencyAppError(
            code="llm_provider_http_error",
            message="llm provider returned non-success response",
            details={"status_code": status_code},
            retryable=False,
        )

    def _parse_response(self, payload: dict) -> LLMCompletionResponse:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise DependencyAppError(
                code="llm_invalid_response",
                message="llm provider response missing choices",
                details={},
                retryable=False,
            )

        first = choices[0]
        if not isinstance(first, dict):
            raise DependencyAppError(
                code="llm_invalid_response",
                message="llm provider choice payload is invalid",
                details={},
                retryable=False,
            )

        message = first.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        text = ""
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            # Compatible with content blocks format.
            blocks: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    item_text = item.get("text")
                    if isinstance(item_text, str):
                        blocks.append(item_text)
            text = "\n".join(blocks).strip()

        if not text:
            raise DependencyAppError(
                code="llm_invalid_response",
                message="llm provider returned empty assistant content",
                details={},
                retryable=False,
            )

        return LLMCompletionResponse(
            text=text,
            model=payload.get("model") if isinstance(payload.get("model"), str) else None,
            finish_reason=first.get("finish_reason") if isinstance(first.get("finish_reason"), str) else None,
            metadata={
                "id": payload.get("id"),
                "usage": payload.get("usage"),
            },
        )

    async def _post_json(
        self,
        *,
        url: str,
        payload: dict,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> httpx.Response:
        if self._client is not None:
            return await self._client.post(url, json=payload, headers=headers, timeout=timeout_seconds)

        async with httpx.AsyncClient() as client:
            return await client.post(url, json=payload, headers=headers, timeout=timeout_seconds)

    async def chat_completion(self, *, request: LLMCompletionRequest) -> LLMCompletionResponse:
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
                        code="llm_invalid_response",
                        message="llm provider response is not a json object",
                        details={},
                        retryable=False,
                    )

                result = self._parse_response(body)
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                self._logger.info(
                    "llm_call_succeeded",
                    extra={
                        "request_id": request.request_id,
                        "trace_id": request.trace_id,
                        "provider_name": "openai_compatible",
                        "operation": "chat_completions",
                        "attempt": attempt,
                        "latency_ms": latency_ms,
                        "fallback_used": False,
                    },
                )
                return result
            except httpx.TimeoutException:
                error = TimeoutAppError(
                    code="llm_timeout",
                    message="llm provider request timed out",
                    details={"timeout_seconds": timeout_seconds},
                )
            except httpx.TransportError:
                error = UnavailableAppError(
                    code="llm_provider_unavailable",
                    message="llm provider transport unavailable",
                    details={},
                )
            except (DependencyAppError, UnavailableAppError, TimeoutAppError) as exc:
                error = exc
            except Exception:
                error = DependencyAppError(
                    code="llm_provider_unavailable",
                    message="llm provider request failed unexpectedly",
                    details={},
                )

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            self._logger.warning(
                "llm_call_failed",
                extra={
                    "request_id": request.request_id,
                    "trace_id": request.trace_id,
                    "provider_name": "openai_compatible",
                    "operation": "chat_completions",
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
            code="llm_retry_exhausted",
            message="llm provider retries exhausted",
            details={"max_retries": self._max_retries},
        )
