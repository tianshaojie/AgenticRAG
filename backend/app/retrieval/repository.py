from __future__ import annotations

import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk
from app.domain.interfaces import ChunkRecord, ScoredChunk, VectorIndex


class RetrievalRepository:
    def __init__(self, *, vector_index: VectorIndex, db: Session | None = None) -> None:
        self._vector_index = vector_index
        self._db = db

    @staticmethod
    def _extract_terms(query: str) -> list[str]:
        terms = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+", query.lower())
        if not terms and query.strip():
            return [query.strip().lower()]
        return terms[:12]

    @staticmethod
    def _score_lexical(content: str, *, terms: list[str], raw_query: str) -> float:
        text = content.lower()
        if not terms:
            return 0.0

        matched = sum(1 for term in terms if term in text)
        score = matched / len(terms)
        if raw_query.lower() in text:
            score = max(score, 0.95)
        return min(score, 1.0)

    def _lexical_fallback(
        self,
        *,
        query_text: str,
        top_k: int,
        score_threshold: float,
    ) -> list[ScoredChunk]:
        if self._db is None:
            return []

        terms = self._extract_terms(query_text)
        if not terms:
            return []

        conditions = [DocumentChunk.content.ilike(f"%{term}%") for term in terms]
        rows = (
            self._db.execute(
                select(DocumentChunk)
                .where(or_(*conditions))
                .limit(max(top_k * 5, 20))
            )
            .scalars()
            .all()
        )

        scored: list[ScoredChunk] = []
        for row in rows:
            score = self._score_lexical(row.content, terms=terms, raw_query=query_text)
            if score < score_threshold:
                continue
            metadata = dict(row.meta or {})
            metadata["retrieval_source"] = "lexical_fallback"
            scored.append(
                ScoredChunk(
                    chunk=ChunkRecord(
                        chunk_id=row.id,
                        document_id=row.document_id,
                        document_version_id=row.document_version_id,
                        content=row.content,
                        chunk_index=row.chunk_index,
                        start_char=row.start_char or 0,
                        end_char=row.end_char or len(row.content),
                        metadata=metadata,
                    ),
                    score=score,
                    distance=max(0.0, 1.0 - score),
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    async def search(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        score_threshold: float,
        model: str,
        query_text: str | None = None,
    ) -> list[ScoredChunk]:
        vector_results = await self._vector_index.search(
            query_vector=query_vector,
            top_k=top_k,
            score_threshold=score_threshold,
            model=model,
        )
        if vector_results:
            return vector_results
        if query_text is None:
            return vector_results
        return self._lexical_fallback(
            query_text=query_text,
            top_k=top_k,
            score_threshold=score_threshold,
        )
