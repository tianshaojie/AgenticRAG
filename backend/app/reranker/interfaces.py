from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class RerankerCandidate:
    candidate_id: str
    document: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RerankRequest:
    query: str
    candidates: list[RerankerCandidate]
    top_n: int
    model: str
    timeout_seconds: float | None = None
    request_id: str = "unknown"
    trace_id: str = "unknown"


@dataclass(slots=True)
class RerankedItem:
    candidate_id: str
    rank: int
    original_index: int
    score: float | None = None


@dataclass(slots=True)
class RerankResponse:
    items: list[RerankedItem]
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RerankerProvider(Protocol):
    async def rerank(self, *, request: RerankRequest) -> RerankResponse:
        """Rerank candidates while preserving original candidate identity references."""
