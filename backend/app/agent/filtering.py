from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from app.agent.interfaces import EvidenceFilter
from app.domain.interfaces import ScoredChunk


class DefaultEvidenceFilter(EvidenceFilter):
    """Conservative evidence filter for reranked results.

    Rules:
    1. Keep original object identity (no remapping).
    2. Drop duplicated chunk ids.
    3. Drop low-score chunks below configured threshold.
    4. Cap chunk count per document to avoid single-document dominance.
    """

    def __init__(self, *, max_chunks_per_document: int) -> None:
        self._max_chunks_per_document = max(1, max_chunks_per_document)

    def filter(
        self,
        *,
        query: str,
        candidates: list[ScoredChunk],
        min_score: float,
        top_n: int,
    ) -> list[ScoredChunk]:
        _ = query
        if not candidates:
            return []

        limit = max(1, top_n)
        seen_chunk_ids: set[UUID] = set()
        per_doc_count: dict[UUID, int] = defaultdict(int)
        filtered: list[ScoredChunk] = []

        for item in candidates:
            if item.chunk.chunk_id in seen_chunk_ids:
                continue
            if item.score < min_score:
                continue
            if per_doc_count[item.chunk.document_id] >= self._max_chunks_per_document:
                continue

            seen_chunk_ids.add(item.chunk.chunk_id)
            per_doc_count[item.chunk.document_id] += 1
            filtered.append(item)
            if len(filtered) >= limit:
                break

        return filtered
