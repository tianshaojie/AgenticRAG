from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ErrorCategory(StrEnum):
    VALIDATION = "validation"
    DEPENDENCY = "dependency"
    TIMEOUT = "timeout"
    INTERNAL = "internal"
    UNAVAILABLE = "unavailable"


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    category: ErrorCategory
    http_status: int
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class ValidationAppError(AppError):
    def __init__(self, *, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.VALIDATION,
            http_status=400,
            details=details or {},
            retryable=False,
        )


class DependencyAppError(AppError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = True,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.DEPENDENCY,
            http_status=502,
            details=details or {},
            retryable=retryable,
        )


class TimeoutAppError(AppError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.TIMEOUT,
            http_status=504,
            details=details or {},
            retryable=True,
        )


class UnavailableAppError(AppError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.UNAVAILABLE,
            http_status=503,
            details=details or {},
            retryable=True,
        )


class InternalAppError(AppError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.INTERNAL,
            http_status=500,
            details=details or {},
            retryable=False,
        )


def classify_http_status(status_code: int) -> ErrorCategory:
    if status_code in {400, 404, 409, 422}:
        return ErrorCategory.VALIDATION
    if status_code == 503:
        return ErrorCategory.UNAVAILABLE
    if status_code == 504:
        return ErrorCategory.TIMEOUT
    if status_code in {502}:
        return ErrorCategory.DEPENDENCY
    return ErrorCategory.INTERNAL
