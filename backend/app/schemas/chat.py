from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Citation
from app.schemas.retrieval import RetrievalResult


class ChatQueryRequest(BaseModel):
    session_id: UUID | None = None
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    score_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    embedding_model: str = Field(default="deterministic-local-v1")


class ChatQueryResponse(BaseModel):
    session_id: UUID
    message_id: UUID
    answer: str
    citations: list[Citation]
    retrieval_results: list[RetrievalResult]
    abstained: bool
    reason: str | None = None
    created_at: datetime
