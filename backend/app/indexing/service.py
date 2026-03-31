from __future__ import annotations

import logging

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.resilience import ResiliencePolicy, call_with_resilience
from app.db.models import Document, DocumentChunk, DocumentVersion
from app.domain.enums import DocumentStatus
from app.domain.interfaces import Chunker, Embedder, VectorIndex


class DocumentIndexingService:
    def __init__(
        self,
        *,
        db: Session,
        chunker: Chunker,
        embedder: Embedder,
        vector_index: VectorIndex,
        settings: Settings,
    ) -> None:
        self._db = db
        self._chunker = chunker
        self._embedder = embedder
        self._vector_index = vector_index
        self._settings = settings
        self._logger = logging.getLogger("app.indexing")

    async def index_document(
        self,
        *,
        document_id,
        embedding_model: str,
        request_id: str,
        timeout_seconds: int,
        trace_id: str | None = None,
    ) -> tuple[int, int]:
        trace_value = trace_id or request_id
        document = self._db.get(Document, document_id)
        if document is None:
            raise ValueError("document_not_found")

        version = self._db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(desc(DocumentVersion.version_number))
            .limit(1)
        ).scalar_one_or_none()

        if version is None:
            raise ValueError("document_version_not_found")

        document.status = DocumentStatus.INDEXING
        self._db.flush()

        self._db.query(DocumentChunk).filter(
            DocumentChunk.document_version_id == version.id
        ).delete(synchronize_session=False)
        self._db.flush()

        chunks = self._chunker.chunk(
            text=version.content_text,
            document_id=document.id,
            document_version_id=version.id,
            metadata={"document_version": version.version_number},
        )

        for chunk in chunks:
            self._db.add(
                DocumentChunk(
                    id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_version_id=chunk.document_version_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    token_count=None,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    meta=chunk.metadata,
                )
            )

        self._db.flush()

        embed_policy = ResiliencePolicy(
            timeout_seconds=float(timeout_seconds),
            max_retries=self._settings.embedding_retry_attempts,
            backoff_base_ms=self._settings.provider_backoff_base_ms,
            backoff_max_ms=self._settings.provider_backoff_max_ms,
        )
        vectors = await call_with_resilience(
            operation="embedding",
            provider_name=type(self._embedder).__name__,
            policy=embed_policy,
            call=lambda: self._embedder.embed(
                inputs=[c.content for c in chunks],
                model=embedding_model,
                timeout_seconds=timeout_seconds,
            ),
            logger=self._logger,
            request_id=request_id,
            trace_id=trace_value,
            document_id=str(document_id),
        )

        upsert_policy = ResiliencePolicy(
            timeout_seconds=float(self._settings.retrieval_timeout_seconds),
            max_retries=self._settings.retrieval_retry_attempts,
            backoff_base_ms=self._settings.provider_backoff_base_ms,
            backoff_max_ms=self._settings.provider_backoff_max_ms,
        )
        await call_with_resilience(
            operation="vector_upsert",
            provider_name=type(self._vector_index).__name__,
            policy=upsert_policy,
            call=lambda: self._vector_index.upsert(
                vectors=[
                    (
                        chunk.chunk_id,
                        vector,
                        {
                            "document_id": str(chunk.document_id),
                            "chunk_index": chunk.chunk_index,
                        },
                    )
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ],
                model=embedding_model,
            ),
            logger=self._logger,
            request_id=request_id,
            trace_id=trace_value,
            document_id=str(document_id),
        )

        document.status = DocumentStatus.INDEXED
        self._db.commit()

        self._logger.info(
            "document_indexed",
            extra={
                "request_id": request_id,
                "trace_id": trace_value,
                "document_id": str(document_id),
                "chunk_count": len(chunks),
                "vector_count": len(vectors),
                "provider_name": type(self._embedder).__name__,
                "fallback_used": False,
            },
        )
        return len(chunks), len(vectors)
