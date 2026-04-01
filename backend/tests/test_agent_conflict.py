from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.evidence import DefaultEvidenceSufficiencyJudge
from app.domain.interfaces import ChunkRecord, ScoredChunk


def _build_scored(content: str, score: float, *, doc_id=None) -> ScoredChunk:
    return ScoredChunk(
        chunk=ChunkRecord(
            chunk_id=uuid4(),
            document_id=doc_id or uuid4(),
            document_version_id=uuid4(),
            content=content,
            chunk_index=0,
            start_char=0,
            end_char=len(content),
            metadata={},
        ),
        score=score,
        distance=1 - score,
    )


def test_evidence_conflict_detection() -> None:
    judge = DefaultEvidenceSufficiencyJudge(min_results=1, min_score=0.3, conflict_delta=0.05)

    shared_doc_1 = uuid4()
    shared_doc_2 = uuid4()
    candidates = [
        _build_scored("信用账户支持融资融券", 0.90, doc_id=shared_doc_1),
        _build_scored("信用账户不支持融资融券", 0.88, doc_id=shared_doc_2),
    ]

    assessed = judge.judge(query="信用账户", candidates=candidates)
    assert assessed.sufficient is True
    assert assessed.conflict is True
    assert assessed.reason == "evidence_conflict"
    assert assessed.conflict_type == "negation_mismatch"
    assert len(assessed.conflict_chunk_ids) == 2
    assert assessed.conflict_score_gap is not None


@pytest.mark.integration
def test_conflict_answer_is_marked_uncertain(client) -> None:
    first = client.post(
        "/documents",
        data={"title": "policy-a"},
        files={"file": ("a.md", "信用账户支持融资融券".encode("utf-8"), "text/markdown")},
    )
    second = client.post(
        "/documents",
        data={"title": "policy-b"},
        files={"file": ("b.md", "信用账户不支持融资融券".encode("utf-8"), "text/markdown")},
    )

    first_id = first.json()["id"]
    second_id = second.json()["id"]

    client.post(f"/documents/{first_id}/index", json={"chunk_size": 128, "chunk_overlap": 16})
    client.post(f"/documents/{second_id}/index", json={"chunk_size": 128, "chunk_overlap": 16})

    response = client.post(
        "/chat/query",
        json={
            "query": "信用账户",
            "top_k": 5,
            "score_threshold": 0.8,
            "embedding_model": "deterministic-local-v1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["abstained"] is False
    assert "uncertain" in payload["answer"].lower()
    assert payload["reason"] == "evidence_conflict"
    assert payload["uncertainty"] is not None
    assert payload["uncertainty"]["is_uncertain"] is True
    assert payload["uncertainty"]["reason"] == "evidence_conflict"
    assert payload["uncertainty"]["conflict_type"] == "negation_mismatch"
    assert len(payload["uncertainty"]["conflict_chunk_ids"]) == 2
