from __future__ import annotations

import re
from abc import ABC
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk
from app.domain.interfaces import ChunkRecord, ScoredChunk


@dataclass(slots=True)
class RouteProviderRequest:
    query: str
    top_k: int
    score_threshold: float
    model: str
    request_id: str = "unknown"
    trace_id: str = "unknown"


class RouteRetrieverProvider(Protocol):
    provider_name: str

    async def retrieve(self, *, request: RouteProviderRequest) -> list[ScoredChunk]:
        """Route-specific retrieval provider contract."""


class _BaseLexicalRouteProvider(RouteRetrieverProvider, ABC):
    def __init__(
        self,
        *,
        db: Session,
        route_name: str,
        retrieval_source: str,
        prefixes: tuple[str, ...],
        stop_terms: set[str] | None = None,
        provider_name: str,
    ) -> None:
        self._db = db
        self._route_name = route_name
        self._retrieval_source = retrieval_source
        self._prefixes = tuple(prefixes)
        self._stop_terms = stop_terms or set()
        self.provider_name = provider_name

    def _normalize_query(self, query: str) -> str:
        normalized = query.strip()
        lowered = normalized.lower()
        for prefix in self._prefixes:
            if lowered.startswith(prefix):
                return normalized[len(prefix) :].strip()
        return normalized

    def _extract_terms(self, query: str) -> list[str]:
        terms = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9_]+", query.lower())
        filtered = [term for term in terms if term not in self._stop_terms]
        return filtered[:16]

    @staticmethod
    def _score(content: str, *, terms: list[str], raw_query: str) -> float:
        if not terms:
            return 0.0

        text = content.lower()
        matched = sum(1 for term in terms if term in text)
        lexical = matched / max(len(terms), 1)
        if raw_query.lower() and raw_query.lower() in text:
            lexical = max(lexical, 0.95)
        return min(1.0, lexical)

    async def retrieve(self, *, request: RouteProviderRequest) -> list[ScoredChunk]:
        _ = request.model, request.request_id, request.trace_id
        normalized_query = self._normalize_query(request.query)
        terms = self._extract_terms(normalized_query)
        if not terms:
            return []

        where_terms = [DocumentChunk.content.ilike(f"%{term}%") for term in terms]
        rows = (
            self._db.execute(
                select(DocumentChunk)
                .where(or_(*where_terms))
                .limit(max(request.top_k * 8, 40))
            )
            .scalars()
            .all()
        )

        scored: list[ScoredChunk] = []
        for row in rows:
            score = self._score(row.content, terms=terms, raw_query=normalized_query)
            if score < request.score_threshold:
                continue
            metadata = dict(row.meta or {})
            metadata["retrieval_source"] = self._retrieval_source
            metadata["route"] = self._route_name
            metadata["route_provider"] = self.provider_name
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
        return scored[: request.top_k]


class SqlLexicalRouteProvider(_BaseLexicalRouteProvider):
    def __init__(self, *, db: Session) -> None:
        super().__init__(
            db=db,
            route_name="sql",
            retrieval_source="sql_route",
            prefixes=("sql:",),
            stop_terms={"select", "from", "where", "group", "by", "order", "limit", "count"},
            provider_name="sql_lexical",
        )


class ApiLexicalRouteProvider(_BaseLexicalRouteProvider):
    def __init__(self, *, db: Session) -> None:
        super().__init__(
            db=db,
            route_name="api",
            retrieval_source="api_route",
            prefixes=("api:",),
            stop_terms={"api", "http", "https"},
            provider_name="api_lexical",
        )


class SqlMockRouteProvider(_BaseLexicalRouteProvider):
    def __init__(self, *, db: Session) -> None:
        super().__init__(
            db=db,
            route_name="sql",
            retrieval_source="sql_route",
            prefixes=("sql:",),
            stop_terms={"select", "from", "where", "group", "by", "order", "limit", "count"},
            provider_name="sql_mock",
        )


class ApiMockRouteProvider(_BaseLexicalRouteProvider):
    def __init__(self, *, db: Session) -> None:
        super().__init__(
            db=db,
            route_name="api",
            retrieval_source="api_route",
            prefixes=("api:",),
            stop_terms={"api", "http", "https"},
            provider_name="api_mock",
        )
