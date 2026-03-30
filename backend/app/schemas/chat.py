from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Citation


class ChatQueryRequest(BaseModel):
    session_id: UUID | None = None
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    rerank_k: int = Field(default=5, ge=1, le=20)


class ChatQueryResponse(BaseModel):
    session_id: UUID
    message_id: UUID
    trace_id: UUID
    answer: str
    citations: list[Citation]
    abstained: bool
    reason: str | None = None
    created_at: datetime
