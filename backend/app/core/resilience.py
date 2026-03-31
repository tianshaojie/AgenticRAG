from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

from app.core.errors import AppError, DependencyAppError, TimeoutAppError

T = TypeVar("T")


@dataclass(slots=True)
class ResiliencePolicy:
    timeout_seconds: float
    max_retries: int
    backoff_base_ms: int
    backoff_max_ms: int


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, AppError):
        return exc.retryable
    return True


async def call_with_resilience(
    *,
    operation: str,
    provider_name: str,
    policy: ResiliencePolicy,
    call: Callable[[], Awaitable[T]],
    logger: logging.Logger,
    request_id: str,
    trace_id: str,
    query_id: str | None = None,
    document_id: str | None = None,
    agent_state: str | None = None,
) -> T:
    attempt = 0
    max_attempts = max(policy.max_retries, 0) + 1

    while attempt < max_attempts:
        attempt += 1
        started = time.perf_counter()

        try:
            result = await asyncio.wait_for(call(), timeout=policy.timeout_seconds)
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "provider_call_succeeded",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "query_id": query_id,
                    "document_id": document_id,
                    "agent_state": agent_state,
                    "provider_name": provider_name,
                    "operation": operation,
                    "attempt": attempt,
                    "latency_ms": latency_ms,
                    "fallback_used": False,
                },
            )
            return result
        except asyncio.TimeoutError:
            normalized_exc: Exception = TimeoutAppError(
                code=f"{operation}_timeout",
                message=f"{operation} timed out",
                details={"provider_name": provider_name, "timeout_seconds": policy.timeout_seconds},
            )
        except AppError as exc:
            normalized_exc = exc
        except Exception as exc:  # pragma: no cover - defensive
            normalized_exc = DependencyAppError(
                code=f"{operation}_dependency_error",
                message=f"{operation} failed due to dependency error",
                details={"provider_name": provider_name, "cause": str(exc)},
            )

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.warning(
            "provider_call_failed",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "query_id": query_id,
                "document_id": document_id,
                "agent_state": agent_state,
                "provider_name": provider_name,
                "operation": operation,
                "attempt": attempt,
                "latency_ms": latency_ms,
                "fallback_used": False,
                "error_code": getattr(normalized_exc, "code", type(normalized_exc).__name__),
            },
        )

        if attempt >= max_attempts or not _is_retryable(normalized_exc):
            raise normalized_exc

        backoff_ms = min(policy.backoff_base_ms * (2 ** (attempt - 1)), policy.backoff_max_ms)
        await asyncio.sleep(backoff_ms / 1000)

    raise DependencyAppError(
        code=f"{operation}_retry_exhausted",
        message=f"{operation} retry attempts exhausted",
        details={"provider_name": provider_name, "max_retries": policy.max_retries},
    )
