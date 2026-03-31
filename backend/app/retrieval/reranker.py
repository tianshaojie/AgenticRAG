from __future__ import annotations

import re

from app.domain.interfaces import Reranker, ScoredChunk


class BasicReranker(Reranker):
    """Simple lexical+vector reranker for Step 4 baseline."""

    @staticmethod
    def _terms(text: str) -> list[str]:
        terms = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+", text.lower())
        return terms[:16]

    async def rerank(self, *, query: str, candidates: list[ScoredChunk], top_n: int) -> list[ScoredChunk]:
        if not candidates:
            return []

        terms = self._terms(query)
        if not terms:
            return candidates[:top_n]

        def combined_score(item: ScoredChunk) -> float:
            content = item.chunk.content.lower()
            lexical_hits = sum(1 for term in terms if term in content)
            lexical_score = lexical_hits / len(terms)
            return 0.65 * item.score + 0.35 * lexical_score

        ranked = sorted(candidates, key=combined_score, reverse=True)
        return ranked[:top_n]
