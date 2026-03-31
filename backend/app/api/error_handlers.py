from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import AppError, ErrorCategory, classify_http_status
from app.observability.metrics import metrics
from app.schemas.errors import ErrorModel, ErrorResponse

logger = logging.getLogger("app.error")


def _request_context(request: Request) -> tuple[str, str]:
    request_id = getattr(request.state, "request_id", "unknown")
    trace_id = getattr(request.state, "trace_id", "unknown")
    return request_id, trace_id


def _build_error_response(
    *,
    code: str,
    category: ErrorCategory,
    message: str,
    request_id: str,
    trace_id: str,
    details: dict[str, Any],
) -> ErrorResponse:
    return ErrorResponse(
        error=ErrorModel(
            code=code,
            category=category.value,
            message=message,
            request_id=request_id,
            trace_id=trace_id,
            details=details,
        )
    )


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    request_id, trace_id = _request_context(request)
    payload = _build_error_response(
        code=exc.code,
        category=exc.category,
        message=exc.message,
        request_id=request_id,
        trace_id=trace_id,
        details=exc.details,
    )
    metrics.increment_error(
        path=request.url.path,
        category=exc.category.value,
        code=exc.code,
    )
    logger.error(
        "app_error",
        extra={
            "request_id": request_id,
            "trace_id": trace_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.http_status,
            "error_code": exc.code,
            "error_category": exc.category.value,
        },
    )
    return JSONResponse(status_code=exc.http_status, content=payload.model_dump())


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id, trace_id = _request_context(request)
    payload = _build_error_response(
        code="request_validation_error",
        category=ErrorCategory.VALIDATION,
        message="Request validation failed",
        request_id=request_id,
        trace_id=trace_id,
        details={"errors": exc.errors()},
    )
    metrics.increment_error(
        path=request.url.path,
        category=ErrorCategory.VALIDATION.value,
        code="request_validation_error",
    )
    logger.warning(
        "validation_error",
        extra={
            "request_id": request_id,
            "trace_id": trace_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": 422,
            "error_code": "request_validation_error",
            "error_category": ErrorCategory.VALIDATION.value,
        },
    )
    return JSONResponse(status_code=422, content=payload.model_dump())


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    request_id, trace_id = _request_context(request)
    category = classify_http_status(exc.status_code)
    detail = exc.detail
    if isinstance(detail, dict):
        message = str(detail.get("message", detail))
        details = detail
    else:
        message = str(detail)
        details = {}

    code = f"http_{exc.status_code}"
    payload = _build_error_response(
        code=code,
        category=category,
        message=message,
        request_id=request_id,
        trace_id=trace_id,
        details=details,
    )
    metrics.increment_error(
        path=request.url.path,
        category=category.value,
        code=code,
    )
    log_method = logger.warning if exc.status_code < 500 else logger.error
    log_method(
        "http_exception",
        extra={
            "request_id": request_id,
            "trace_id": trace_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "error_code": code,
            "error_category": category.value,
        },
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    request_id, trace_id = _request_context(request)
    payload = _build_error_response(
        code="internal_error",
        category=ErrorCategory.INTERNAL,
        message="Internal server error",
        request_id=request_id,
        trace_id=trace_id,
        details={},
    )
    metrics.increment_error(
        path=request.url.path,
        category=ErrorCategory.INTERNAL.value,
        code="internal_error",
    )
    logger.exception(
        "unhandled_exception",
        extra={
            "request_id": request_id,
            "trace_id": trace_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": 500,
            "error_code": "internal_error",
            "error_category": ErrorCategory.INTERNAL.value,
        },
    )
    return JSONResponse(status_code=500, content=payload.model_dump())
