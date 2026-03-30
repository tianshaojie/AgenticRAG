from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_id: UUID
    document_id: UUID
    quote: str = Field(min_length=1)
    score: float


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


class RequestMetadata(BaseModel):
    request_id: str
    trace_id: str
