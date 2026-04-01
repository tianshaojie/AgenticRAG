from __future__ import annotations

from uuid import uuid4

from app.agent.filtering import DefaultEvidenceFilter
from app.domain.interfaces import ChunkRecord, ScoredChunk


def _chunk(*, document_id, chunk_id, score: float, content: str = "evidence") -> ScoredChunk:
    return ScoredChunk(
        chunk=ChunkRecord(
            chunk_id=chunk_id,
            document_id=document_id,
            document_version_id=uuid4(),
            content=content,
            chunk_index=0,
            start_char=0,
            end_char=len(content),
            metadata={},
        ),
        score=score,
        distance=1.0 - score,
    )


def test_evidence_filter_dedup_score_and_doc_cap() -> None:
    doc_a = uuid4()
    doc_b = uuid4()
    shared_chunk = uuid4()

    candidates = [
        _chunk(document_id=doc_a, chunk_id=shared_chunk, score=0.95, content="a1"),
        _chunk(document_id=doc_a, chunk_id=shared_chunk, score=0.94, content="a1-dup"),
        _chunk(document_id=doc_a, chunk_id=uuid4(), score=0.92, content="a2"),
        _chunk(document_id=doc_a, chunk_id=uuid4(), score=0.91, content="a3-over-cap"),
        _chunk(document_id=doc_b, chunk_id=uuid4(), score=0.88, content="b1"),
        _chunk(document_id=doc_b, chunk_id=uuid4(), score=0.20, content="b2-low-score"),
    ]

    evidence_filter = DefaultEvidenceFilter(max_chunks_per_document=2)
    filtered = evidence_filter.filter(
        query="信用账户",
        candidates=candidates,
        min_score=0.30,
        top_n=5,
    )

    assert [item.chunk.content for item in filtered] == ["a1", "a2", "b1"]
    assert all(item.score >= 0.30 for item in filtered)
    assert len({item.chunk.chunk_id for item in filtered}) == len(filtered)
