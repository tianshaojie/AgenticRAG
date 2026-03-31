from __future__ import annotations

from app.domain.interfaces import AnswerGenerator, CitationRecord, GeneratedAnswer


class ThresholdAnswerGenerator(AnswerGenerator):
    def __init__(self, *, min_citations: int, min_score: float) -> None:
        self._min_citations = min_citations
        self._min_score = min_score

    async def generate(self, *, query: str, citations: list[CitationRecord]) -> GeneratedAnswer:
        _ = query
        if len(citations) < self._min_citations:
            return GeneratedAnswer(
                text="Insufficient evidence to answer reliably.",
                citations=citations,
                abstained=True,
                reason="insufficient_citation_count",
            )

        if max((c.score for c in citations), default=0.0) < self._min_score:
            return GeneratedAnswer(
                text="Insufficient evidence confidence to answer reliably.",
                citations=citations,
                abstained=True,
                reason="insufficient_citation_score",
            )

        top_quotes = "\n".join(f"- {c.quote}" for c in citations[:2])
        return GeneratedAnswer(
            text=f"Based on the retrieved evidence:\n{top_quotes}",
            citations=citations,
            abstained=False,
            reason=None,
        )
