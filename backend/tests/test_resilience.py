from __future__ import annotations

import asyncio
import logging

import pytest

from app.core.errors import DependencyAppError, TimeoutAppError
from app.core.resilience import ResiliencePolicy, call_with_resilience


@pytest.mark.asyncio
async def test_call_with_resilience_retries_then_success() -> None:
    logger = logging.getLogger("tests.resilience")
    attempts = {"count": 0}

    async def flaky_call() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise DependencyAppError(code="provider_down", message="provider down")
        return "ok"

    result = await call_with_resilience(
        operation="retrieval",
        provider_name="FlakyProvider",
        policy=ResiliencePolicy(timeout_seconds=1.0, max_retries=3, backoff_base_ms=1, backoff_max_ms=2),
        call=flaky_call,
        logger=logger,
        request_id="req-resilience",
        trace_id="trace-resilience",
        query_id="query-resilience",
        agent_state="RETRIEVE",
    )

    assert result == "ok"
    assert attempts["count"] == 3


@pytest.mark.asyncio
async def test_call_with_resilience_timeout() -> None:
    logger = logging.getLogger("tests.resilience")

    async def slow_call() -> str:
        await asyncio.sleep(0.05)
        return "late"

    with pytest.raises(TimeoutAppError) as exc_info:
        await call_with_resilience(
            operation="generation",
            provider_name="SlowProvider",
            policy=ResiliencePolicy(
                timeout_seconds=0.01,
                max_retries=1,
                backoff_base_ms=1,
                backoff_max_ms=2,
            ),
            call=slow_call,
            logger=logger,
            request_id="req-timeout",
            trace_id="trace-timeout",
            query_id="query-timeout",
            agent_state="GENERATE_ANSWER",
        )

    assert exc_info.value.code == "generation_timeout"
