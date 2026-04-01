from __future__ import annotations

from typing import Any

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

    def _detect_conflict(self, candidates: list[ScoredChunk]) -> dict[str, Any] | None:
        if len(candidates) < 2:
            return None

        # Compare top evidence pairs so conflict can still be detected when a neutral
        # chunk appears between two contradictory chunks in rank order.
        top_candidates = sorted(candidates, key=lambda item: item.score, reverse=True)[:4]
        best_conflict: tuple[ScoredChunk, ScoredChunk, float] | None = None
        for idx, first in enumerate(top_candidates):
            for second in top_candidates[idx + 1 :]:
                if first.chunk.document_id == second.chunk.document_id:
                    continue
                score_gap = abs(first.score - second.score)
                if score_gap > self._conflict_delta:
                    continue
                if self._has_negation(first.chunk.content) == self._has_negation(second.chunk.content):
                    continue
                if best_conflict is None or score_gap < best_conflict[2]:
                    best_conflict = (first, second, score_gap)

        if best_conflict is None:
            return None

        first, second, score_gap = best_conflict
        return {
            "type": "negation_mismatch",
            "chunk_ids": [first.chunk.chunk_id, second.chunk.chunk_id],
            "score_gap": score_gap,
        }

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

        conflict_signal = self._detect_conflict(candidates)
        conflict = conflict_signal is not None
        return EvidenceAssessment(
            sufficient=True,
            reason="evidence_conflict" if conflict else "evidence_sufficient",
            conflict=conflict,
            needs_rewrite=False,
            conflict_type=str(conflict_signal["type"]) if conflict_signal else None,
            conflict_chunk_ids=list(conflict_signal["chunk_ids"]) if conflict_signal else [],
            conflict_score_gap=float(conflict_signal["score_gap"]) if conflict_signal else None,
        )
