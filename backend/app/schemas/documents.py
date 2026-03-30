from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import DocumentStatus


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    source_uri: str = Field(min_length=1, max_length=2048)
    mime_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRead(BaseModel):
    id: UUID
    title: str
    source_uri: str
    mime_type: str | None
    status: DocumentStatus
    metadata: dict[str, Any]
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentRead]
    total: int


class DocumentIndexRequest(BaseModel):
    embedding_model: str = Field(default="stub-embedding-model")
    chunk_size: int = Field(default=512, ge=64, le=4096)
    chunk_overlap: int = Field(default=64, ge=0, le=512)


class DocumentIndexResponse(BaseModel):
    document_id: UUID
    status: str
    accepted: bool
