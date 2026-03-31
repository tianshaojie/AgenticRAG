from __future__ import annotations

import re

from app.reranker.interfaces import (
    RerankRequest,
    RerankResponse,
    RerankedItem,
    RerankerProvider,
)


class MockRerankerProvider(RerankerProvider):
    """Deterministic local reranker used for tests/offline flows."""

    @staticmethod
    def _terms(text: str) -> list[str]:
        terms = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+", text.lower())
        return terms[:16]

    async def rerank(self, *, request: RerankRequest) -> RerankResponse:
        terms = self._terms(request.query)

        def lexical_score(text: str) -> float:
            lowered = text.lower()
            if not terms:
                return 0.0
            hits = sum(1 for term in terms if term in lowered)
            return hits / max(len(terms), 1)

        ranked = sorted(
            enumerate(request.candidates),
            key=lambda item: lexical_score(item[1].document),
            reverse=True,
        )

        limit = min(max(request.top_n, 1), len(ranked))
        items: list[RerankedItem] = []
        for rank, (original_index, candidate) in enumerate(ranked[:limit], start=1):
            items.append(
                RerankedItem(
                    candidate_id=candidate.candidate_id,
                    rank=rank,
                    original_index=original_index,
                    score=lexical_score(candidate.document),
                )
            )

        return RerankResponse(
            items=items,
            model="mock-reranker-v1",
            metadata={"provider": "mock"},
        )
