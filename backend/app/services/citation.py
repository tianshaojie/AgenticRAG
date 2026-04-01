from __future__ import annotations

from app.domain.interfaces import CitationAssembler, CitationRecord, ScoredChunk


class BasicCitationAssembler(CitationAssembler):
    def __init__(self, *, quote_max_chars: int = 280) -> None:
        self.quote_max_chars = quote_max_chars

    def assemble(self, *, ranked_chunks: list[ScoredChunk]) -> list[CitationRecord]:
        citations: list[CitationRecord] = []
        for item in ranked_chunks:
            chunk_content_length = len(item.chunk.content)
            raw_span_start = int(item.chunk.start_char)
            raw_span_end = int(item.chunk.end_char)
            local_span_start = 0
            local_span_end = max(0, raw_span_end - raw_span_start)
            if local_span_end <= 0 or local_span_end > chunk_content_length:
                local_span_end = chunk_content_length
            citations.append(
                CitationRecord(
                    chunk_id=item.chunk.chunk_id,
                    document_id=item.chunk.document_id,
                    quote=item.chunk.content[: self.quote_max_chars],
                    score=item.score,
                    start_char=local_span_start,
                    end_char=local_span_end,
                )
            )
        return citations
