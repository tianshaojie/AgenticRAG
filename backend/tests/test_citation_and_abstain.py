from uuid import uuid4

import pytest

from app.domain.interfaces import ChunkRecord, ScoredChunk
from app.services.answer import ThresholdAnswerGenerator
from app.services.citation import BasicCitationAssembler


@pytest.mark.asyncio
async def test_abstain_when_no_evidence() -> None:
    generator = ThresholdAnswerGenerator(min_citations=1, min_score=0.5)
    result = await generator.generate(query="q", citations=[])
    assert result.abstained is True
    assert result.reason == "insufficient_citation_count"


def test_citation_contains_span_mapping() -> None:
    assembler = BasicCitationAssembler()
    scored = [
        ScoredChunk(
            chunk=ChunkRecord(
                chunk_id=uuid4(),
                document_id=uuid4(),
                document_version_id=uuid4(),
                content="hello world",
                chunk_index=0,
                start_char=5,
                end_char=16,
                metadata={},
            ),
            score=0.88,
            distance=0.12,
        )
    ]

    citations = assembler.assemble(ranked_chunks=scored)
    assert len(citations) == 1
    assert citations[0].start_char == 0
    assert citations[0].end_char == len("hello world")
