from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.observability.metrics import metrics


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))

        request.state.request_id = request_id
        request.state.trace_id = trace_id

        start = time.perf_counter()
        logger = logging.getLogger("app.request")
        metrics.increment_request(path=request.url.path)

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            metrics.observe_latency(latency_ms=duration_ms)

            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )

            response_obj = locals().get("response")
            if response_obj is not None:
                response_obj.headers["X-Request-ID"] = request_id
                response_obj.headers["X-Trace-ID"] = trace_id
