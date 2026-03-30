from __future__ import annotations

from typing import Any
from uuid import UUID

from app.domain.interfaces import ScoredChunk, VectorIndex


class PgVectorIndex(VectorIndex):
    """Default VectorIndex implementation based on PostgreSQL + pgvector.

    Implementation intentionally deferred to a later phase.
    """

    async def upsert(self, *, vectors: list[tuple[UUID, list[float], dict[str, Any]]]) -> None:
        _ = vectors
        raise NotImplementedError("PgVectorIndex.upsert is out of scope for Step 1")

    async def search(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        _ = (query_vector, top_k, filters)
        raise NotImplementedError("PgVectorIndex.search is out of scope for Step 1")
