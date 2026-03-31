from __future__ import annotations

import pytest

from app.core.errors import DependencyAppError
from app.retrieval.service import PgVectorRetriever


@pytest.mark.integration
def test_error_response_schema_validation(client) -> None:
    response = client.post(
        "/documents",
        data={"title": "bad-metadata", "metadata_json": "[]"},
        files={"file": ("doc.md", b"hello", "text/markdown")},
    )

    assert response.status_code == 400
    payload = response.json()
    assert "error" in payload
    assert payload["error"]["category"] == "validation"
    assert payload["error"]["request_id"]
    assert payload["error"]["trace_id"]


@pytest.mark.integration
def test_health_and_ready_include_pgvector_checks(client) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    health_body = health.json()
    check_names = {item["name"] for item in health_body["checks"]}
    assert "database" in check_names
    assert "pgvector_extension" in check_names
    assert "pgvector_similarity" in check_names

    ready = client.get("/ready")
    assert ready.status_code == 200
    ready_body = ready.json()
    ready_check_names = {item["name"] for item in ready_body["checks"]}
    assert "database" in ready_check_names
    assert "pgvector_extension" in ready_check_names
    assert "pgvector_similarity" in ready_check_names
    assert "fallback_ratio" in ready_body["summary"]


@pytest.mark.integration
def test_trace_fallback_visible_when_retrieval_dependency_fails(client, monkeypatch) -> None:
    async def broken_retrieve(self, *, query: str, top_k: int, score_threshold: float, model: str):
        _ = (self, query, top_k, score_threshold, model)
        raise DependencyAppError(code="retrieval_unavailable", message="retrieval unavailable")

    monkeypatch.setattr(PgVectorRetriever, "retrieve", broken_retrieve)

    response = client.post(
        "/chat/query",
        json={
            "query": "fallback test",
            "top_k": 3,
            "score_threshold": 0.2,
            "embedding_model": "deterministic-local-v1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["abstained"] is True
    assert payload["reason"] == "retrieval_failure_fallback"

    trace = client.get(f"/chat/{payload['session_id']}/trace")
    assert trace.status_code == 200
    trace_body = trace.json()
    retrieve_step = next(step for step in trace_body["steps"] if step["state"] == "RETRIEVE")
    assert retrieve_step["fallback"] is True
    assert retrieve_step["output_payload"]["fallback_stage"] == "retrieval"
