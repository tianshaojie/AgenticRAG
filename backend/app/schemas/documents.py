from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import DocumentStatus


class DocumentRead(BaseModel):
    id: UUID
    title: str
    source_uri: str
    mime_type: str | None
    status: DocumentStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentRead]
    total: int


class DocumentIndexRequest(BaseModel):
    embedding_model: str = Field(default="deterministic-local-v1")
    chunk_size: int = Field(default=512, ge=64, le=4096)
    chunk_overlap: int = Field(default=64, ge=0, le=1024)


class DocumentIndexResponse(BaseModel):
    document_id: UUID
    status: str
    chunk_count: int
    vector_count: int
