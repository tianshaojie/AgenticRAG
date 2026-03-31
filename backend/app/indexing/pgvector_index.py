from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import ChunkVector, DocumentChunk
from app.domain.interfaces import ChunkRecord, ScoredChunk, VectorIndex


class PgVectorIndex(VectorIndex):
    """PostgreSQL + pgvector backed VectorIndex."""

    def __init__(self, *, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings

    def _distance_expr(self, query_vector: list[float]):
        metric = self._settings.vector_distance_metric
        if metric == "cosine":
            return ChunkVector.embedding.cosine_distance(query_vector)
        if metric == "l2":
            return ChunkVector.embedding.l2_distance(query_vector)
        return ChunkVector.embedding.max_inner_product(query_vector)

    def _score_from_distance(self, distance: float) -> float:
        metric = self._settings.vector_distance_metric
        if metric == "cosine":
            return max(0.0, 1.0 - distance)
        if metric == "l2":
            return 1.0 / (1.0 + max(distance, 0.0))
        return max(0.0, -distance)

    async def upsert(self, *, vectors: list[tuple[UUID, list[float], dict[str, Any]]], model: str) -> None:
        for chunk_id, embedding, meta in vectors:
            if len(embedding) != self._settings.vector_dim:
                raise ValueError(
                    f"Vector dim mismatch: got {len(embedding)}, expected {self._settings.vector_dim}"
                )

            existing = self._db.execute(
                select(ChunkVector).where(
                    ChunkVector.chunk_id == chunk_id,
                    ChunkVector.embedding_model == model,
                )
            ).scalar_one_or_none()

            if existing is None:
                self._db.add(
                    ChunkVector(
                        chunk_id=chunk_id,
                        embedding_model=model,
                        embedding_dim=self._settings.vector_dim,
                        embedding=embedding,
                        meta=meta,
                    )
                )
            else:
                existing.embedding = embedding
                existing.embedding_dim = self._settings.vector_dim
                existing.meta = meta

    async def search(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        score_threshold: float,
        model: str,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        distance_expr = self._distance_expr(query_vector)

        stmt: Select[tuple[DocumentChunk, float]] = (
            select(DocumentChunk, distance_expr.label("distance"))
            .join(ChunkVector, ChunkVector.chunk_id == DocumentChunk.id)
            .where(ChunkVector.embedding_model == model)
            .order_by(distance_expr)
            .limit(top_k)
        )

        if filters:
            doc_id = filters.get("document_id")
            if doc_id:
                stmt = stmt.where(DocumentChunk.document_id == doc_id)

            metadata_contains = filters.get("metadata_contains")
            if metadata_contains:
                stmt = stmt.where(DocumentChunk.meta.contains(metadata_contains))

        rows = self._db.execute(stmt).all()
        out: list[ScoredChunk] = []
        for chunk_row, distance in rows:
            distance_value = float(distance)
            score = self._score_from_distance(distance_value)
            if score < score_threshold:
                continue

            out.append(
                ScoredChunk(
                    chunk=ChunkRecord(
                        chunk_id=chunk_row.id,
                        document_id=chunk_row.document_id,
                        document_version_id=chunk_row.document_version_id,
                        content=chunk_row.content,
                        chunk_index=chunk_row.chunk_index,
                        start_char=chunk_row.start_char or 0,
                        end_char=chunk_row.end_char or len(chunk_row.content),
                        metadata=chunk_row.meta,
                    ),
                    score=score,
                    distance=distance_value,
                )
            )

        return out
