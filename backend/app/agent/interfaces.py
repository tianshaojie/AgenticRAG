from __future__ import annotations

from typing import Protocol

from app.agent.models import EvidenceAssessment, QueryAnalysis, RouteDecision
from app.domain.interfaces import ScoredChunk


class QueryRewriteStrategy(Protocol):
    def rewrite(self, *, query: str, attempt: int, reason: str) -> str:
        """Return deterministic rewritten query."""


class EvidenceSufficiencyJudge(Protocol):
    def judge(self, *, query: str, candidates: list[ScoredChunk]) -> EvidenceAssessment:
        """Assess whether evidence is sufficient and whether conflict exists."""


class QueryAnalyzer(Protocol):
    def analyze(self, *, query: str, min_query_chars: int) -> QueryAnalysis:
        """Analyze intent, normalize query text, and decide if retrieval is needed."""


class QueryRouter(Protocol):
    def route(self, *, analysis: QueryAnalysis, available_routes: list[str]) -> RouteDecision:
        """Choose retrieval route from available tools with explicit fallback decision."""


class EvidenceFilter(Protocol):
    def filter(
        self,
        *,
        query: str,
        candidates: list[ScoredChunk],
        min_score: float,
        top_n: int,
    ) -> list[ScoredChunk]:
        """Filter/dedupe reranked evidence while preserving candidate identity."""
