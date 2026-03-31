from __future__ import annotations

from typing import Protocol

from app.agent.models import EvidenceAssessment
from app.domain.interfaces import ScoredChunk


class QueryRewriteStrategy(Protocol):
    def rewrite(self, *, query: str, attempt: int, reason: str) -> str:
        """Return deterministic rewritten query."""


class EvidenceSufficiencyJudge(Protocol):
    def judge(self, *, query: str, candidates: list[ScoredChunk]) -> EvidenceAssessment:
        """Assess whether evidence is sufficient and whether conflict exists."""
