from __future__ import annotations

from app.core.config import Settings
from app.domain.interfaces import Embedder, Retriever, ScoredChunk
from app.retrieval.repository import RetrievalRepository


class PgVectorRetriever(Retriever):
    def __init__(
        self,
        *,
        embedder: Embedder,
        repository: RetrievalRepository,
        settings: Settings,
    ) -> None:
        self._embedder = embedder
        self._repository = repository
        self._settings = settings

    async def retrieve(
        self,
        *,
        query: str,
        top_k: int,
        score_threshold: float,
        model: str,
    ) -> list[ScoredChunk]:
        query_vector = (
            await self._embedder.embed(
                inputs=[query],
                model=model,
                timeout_seconds=self._settings.embedding_timeout_seconds,
            )
        )[0]

        return await self._repository.search(
            query_vector=query_vector,
            top_k=top_k,
            score_threshold=score_threshold,
            model=model,
            query_text=query,
        )
