from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.models import AgentTrace


@pytest.mark.integration
def test_get_chat_trace_and_persistence(client, db_session) -> None:
    create = client.post(
        "/documents",
        data={"title": "trace-doc"},
        files={"file": ("trace.md", b"service level objective is 99.9%", "text/markdown")},
    )
    assert create.status_code == 201
    doc_id = create.json()["id"]

    index = client.post(
        f"/documents/{doc_id}/index",
        json={"embedding_model": "deterministic-local-v1", "chunk_size": 128, "chunk_overlap": 16},
    )
    assert index.status_code == 200

    chat = client.post(
        "/chat/query",
        json={
            "query": "service level objective",
            "top_k": 5,
            "score_threshold": 0.1,
            "embedding_model": "deterministic-local-v1",
        },
    )
    assert chat.status_code == 200
    session_id = chat.json()["session_id"]

    trace_resp = client.get(f"/chat/{session_id}/trace")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()

    assert trace["session_id"] == session_id
    assert len(trace["steps"]) >= 1
    assert trace["steps"][0]["state"] == "INIT"
    assert "input_summary" in trace["steps"][0]
    assert "output_summary" in trace["steps"][0]

    persisted = db_session.execute(
        select(AgentTrace).where(AgentTrace.session_id == session_id)
    ).scalar_one()
    assert persisted.assistant_message_id is not None
    assert persisted.end_state in {"COMPLETE", "ABSTAIN", "FAILED"}
