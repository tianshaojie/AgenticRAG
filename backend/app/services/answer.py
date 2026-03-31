from __future__ import annotations

from app.llm.interfaces import LLMCompletionRequest, LLMMessage, LLMProvider
from app.domain.interfaces import AnswerGenerator, CitationRecord, GeneratedAnswer


class ThresholdAnswerGenerator(AnswerGenerator):
    def __init__(
        self,
        *,
        min_citations: int,
        min_score: float,
        llm_provider: LLMProvider | None = None,
        llm_model: str = "mock-llm-v1",
        llm_temperature: float | None = 0.2,
        llm_max_tokens: int | None = 512,
        llm_timeout_seconds: int | None = 15,
    ) -> None:
        self._min_citations = min_citations
        self._min_score = min_score
        self._llm_provider = llm_provider
        self._llm_model = llm_model
        self._llm_temperature = llm_temperature
        self._llm_max_tokens = llm_max_tokens
        self._llm_timeout_seconds = llm_timeout_seconds

    def _fallback_text(self, *, citations: list[CitationRecord]) -> str:
        top_quotes = "\n".join(f"- {c.quote}" for c in citations[:2])
        return f"Based on the retrieved evidence:\n{top_quotes}"

    def _messages(self, *, query: str, citations: list[CitationRecord]) -> list[LLMMessage]:
        evidence_lines = "\n".join(
            f"- [doc={c.document_id} chunk={c.chunk_id} span={c.start_char}:{c.end_char}] {c.quote}"
            for c in citations[:4]
        )
        return [
            LLMMessage(
                role="system",
                content=(
                    "Answer strictly from provided evidence. If evidence conflicts, mention uncertainty. "
                    "Do not fabricate facts."
                ),
            ),
            LLMMessage(
                role="user",
                content=f"Question:\n{query}\n\nEvidence:\n{evidence_lines}",
            ),
        ]

    async def generate(
        self,
        *,
        query: str,
        citations: list[CitationRecord],
        request_id: str = "unknown",
        trace_id: str = "unknown",
    ) -> GeneratedAnswer:
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

        if self._llm_provider is None:
            return GeneratedAnswer(
                text=self._fallback_text(citations=citations),
                citations=citations,
                abstained=False,
                reason=None,
            )

        completion = await self._llm_provider.chat_completion(
            request=LLMCompletionRequest(
                messages=self._messages(query=query, citations=citations),
                model=self._llm_model,
                temperature=self._llm_temperature,
                max_tokens=self._llm_max_tokens,
                timeout_seconds=float(self._llm_timeout_seconds) if self._llm_timeout_seconds else None,
                request_id=request_id,
                trace_id=trace_id,
            )
        )
        answer_text = completion.text.strip() or self._fallback_text(citations=citations)
        return GeneratedAnswer(
            text=answer_text,
            citations=citations,
            abstained=False,
            reason=None,
        )
