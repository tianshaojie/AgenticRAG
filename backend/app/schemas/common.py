from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CitationSpan(BaseModel):
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)


class Citation(BaseModel):
    chunk_id: UUID
    document_id: UUID
    quote: str = Field(min_length=1)
    score: float
    span: CitationSpan


class HealthCheck(BaseModel):
    name: str
    status: Literal["ok", "degraded", "failed"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "failed"]
    service: str
    timestamp: datetime
    checks: list[HealthCheck] = Field(default_factory=list)


class ReadyResponse(BaseModel):
    status: Literal["ok", "degraded", "failed"]
    checks: list[HealthCheck]
    summary: dict[str, str] = Field(default_factory=dict)


class RequestMetadata(BaseModel):
    request_id: str
    trace_id: str
