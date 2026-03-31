from __future__ import annotations

from app.domain.interfaces import AnswerGenerator, CitationAssembler, CitationRecord, GeneratedAnswer, ScoredChunk


class PassthroughCitationAssembler(CitationAssembler):
    def assemble(self, *, ranked_chunks: list[ScoredChunk]) -> list[CitationRecord]:
        citations: list[CitationRecord] = []
        for item in ranked_chunks:
            citations.append(
                CitationRecord(
                    chunk_id=item.chunk.chunk_id,
                    document_id=item.chunk.document_id,
                    quote=item.chunk.content[:280],
                    score=item.score,
                    start_char=item.chunk.start_char,
                    end_char=item.chunk.end_char,
                )
            )
        return citations


class ConservativeAnswerGenerator(AnswerGenerator):
    async def generate(self, *, query: str, citations: list[CitationRecord]) -> GeneratedAnswer:
        _ = query
        if not citations:
            return GeneratedAnswer(
                text="Insufficient evidence to answer reliably.",
                citations=[],
                abstained=True,
                reason="no_citations",
            )

        return GeneratedAnswer(
            text="This is a placeholder answer generated from cited chunks.",
            citations=citations,
            abstained=False,
            reason=None,
        )
