from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorModel(BaseModel):
    code: str = Field(min_length=1)
    category: str = Field(min_length=1)
    message: str = Field(min_length=1)
    request_id: str
    trace_id: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorModel
