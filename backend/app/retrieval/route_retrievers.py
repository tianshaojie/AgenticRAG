from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.interfaces import ChunkRecord, Retriever, ScoredChunk
from app.retrieval.route_providers import (
    ApiLexicalRouteProvider,
    RouteProviderRequest,
    RouteRetrieverProvider,
    SqlLexicalRouteProvider,
)


class _ProviderRouteRetriever(Retriever):
    def __init__(
        self,
        *,
        route_name: str,
        retrieval_source: str,
        provider: RouteRetrieverProvider,
    ) -> None:
        self._route_name = route_name
        self._retrieval_source = retrieval_source
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    async def retrieve(
        self,
        *,
        query: str,
        top_k: int,
        score_threshold: float,
        model: str,
    ) -> list[ScoredChunk]:
        response = await self._provider.retrieve(
            request=RouteProviderRequest(
                query=query,
                top_k=top_k,
                score_threshold=score_threshold,
                model=model,
            )
        )

        normalized: list[ScoredChunk] = []
        for item in response:
            metadata = dict(item.chunk.metadata or {})
            metadata.setdefault("route", self._route_name)
            metadata.setdefault("retrieval_source", self._retrieval_source)
            metadata.setdefault("route_provider", self._provider.provider_name)
            normalized.append(
                ScoredChunk(
                    chunk=ChunkRecord(
                        chunk_id=item.chunk.chunk_id,
                        document_id=item.chunk.document_id,
                        document_version_id=item.chunk.document_version_id,
                        content=item.chunk.content,
                        chunk_index=item.chunk.chunk_index,
                        start_char=item.chunk.start_char,
                        end_char=item.chunk.end_char,
                        metadata=metadata,
                    ),
                    score=item.score,
                    distance=item.distance,
                )
            )

        normalized.sort(key=lambda scored: scored.score, reverse=True)
        return normalized[:top_k]


class SqlRouteRetriever(_ProviderRouteRetriever):
    def __init__(
        self,
        *,
        db: Session | None = None,
        provider: RouteRetrieverProvider | None = None,
    ) -> None:
        if provider is None:
            if db is None:
                raise ValueError("db is required when provider is not supplied")
            provider = SqlLexicalRouteProvider(db=db)
        super().__init__(route_name="sql", retrieval_source="sql_route", provider=provider)


class ApiRouteRetriever(_ProviderRouteRetriever):
    def __init__(
        self,
        *,
        db: Session | None = None,
        provider: RouteRetrieverProvider | None = None,
    ) -> None:
        if provider is None:
            if db is None:
                raise ValueError("db is required when provider is not supplied")
            provider = ApiLexicalRouteProvider(db=db)
        super().__init__(route_name="api", retrieval_source="api_route", provider=provider)
