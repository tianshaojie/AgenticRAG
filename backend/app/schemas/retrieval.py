from uuid import UUID

from pydantic import BaseModel


class RetrievalResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    score: float
    distance: float
    content_preview: str
