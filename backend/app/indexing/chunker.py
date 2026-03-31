from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from app.domain.interfaces import ChunkRecord


class SlidingWindowChunker:
    def __init__(self, *, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(
        self,
        *,
        text: str,
        document_id: UUID,
        document_version_id: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> list[ChunkRecord]:
        if not text:
            return []

        records: list[ChunkRecord] = []
        step = self.chunk_size - self.chunk_overlap
        chunk_index = 0

        for start in range(0, len(text), step):
            end = min(start + self.chunk_size, len(text))
            content = text[start:end]
            if not content.strip():
                continue

            records.append(
                ChunkRecord(
                    chunk_id=uuid.uuid4(),
                    document_id=document_id,
                    document_version_id=document_version_id,
                    content=content,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end,
                    metadata=metadata or {},
                )
            )
            chunk_index += 1

            if end >= len(text):
                break

        return records
