from __future__ import annotations

from app.agent.interfaces import EvidenceSufficiencyJudge
from app.agent.models import EvidenceAssessment
from app.domain.interfaces import ScoredChunk


class DefaultEvidenceSufficiencyJudge(EvidenceSufficiencyJudge):
    def __init__(
        self,
        *,
        min_results: int,
        min_score: float,
        conflict_delta: float,
    ) -> None:
        self._min_results = min_results
        self._min_score = min_score
        self._conflict_delta = conflict_delta

    @staticmethod
    def _has_negation(text: str) -> bool:
        lower = text.lower()
        markers = [" not ", " no ", " never ", "无", "不", "未", "否"]
        return any(token in lower for token in markers)

    def _detect_conflict(self, candidates: list[ScoredChunk]) -> bool:
        if len(candidates) < 2:
            return False

        first, second = candidates[0], candidates[1]
        if first.chunk.document_id == second.chunk.document_id:
            return False
        if abs(first.score - second.score) > self._conflict_delta:
            return False

        return self._has_negation(first.chunk.content) != self._has_negation(second.chunk.content)

    def judge(self, *, query: str, candidates: list[ScoredChunk]) -> EvidenceAssessment:
        _ = query
        if not candidates:
            return EvidenceAssessment(
                sufficient=False,
                reason="no_retrieved_evidence",
                conflict=False,
                needs_rewrite=True,
            )

        top_score = max(item.score for item in candidates)
        if len(candidates) < self._min_results:
            return EvidenceAssessment(
                sufficient=False,
                reason="insufficient_result_count",
                conflict=False,
                needs_rewrite=True,
            )

        if top_score < self._min_score:
            return EvidenceAssessment(
                sufficient=False,
                reason="insufficient_result_score",
                conflict=False,
                needs_rewrite=True,
            )

        conflict = self._detect_conflict(candidates)
        return EvidenceAssessment(
            sufficient=True,
            reason="evidence_conflict" if conflict else "evidence_sufficient",
            conflict=conflict,
            needs_rewrite=False,
        )
