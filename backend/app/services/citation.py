from __future__ import annotations

from app.domain.interfaces import CitationAssembler, CitationRecord, ScoredChunk


class BasicCitationAssembler(CitationAssembler):
    def __init__(self, *, quote_max_chars: int = 280) -> None:
        self.quote_max_chars = quote_max_chars

    def assemble(self, *, ranked_chunks: list[ScoredChunk]) -> list[CitationRecord]:
        citations: list[CitationRecord] = []
        for item in ranked_chunks:
            citations.append(
                CitationRecord(
                    chunk_id=item.chunk.chunk_id,
                    document_id=item.chunk.document_id,
                    quote=item.chunk.content[: self.quote_max_chars],
                    score=item.score,
                    start_char=item.chunk.start_char,
                    end_char=item.chunk.end_char,
                )
            )
        return citations
