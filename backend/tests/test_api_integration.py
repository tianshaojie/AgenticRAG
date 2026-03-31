import json

import pytest


@pytest.mark.integration
def test_document_index_and_chat_api_flow(client) -> None:
    create_resp = client.post(
        "/documents",
        data={"title": "Doc API", "metadata_json": json.dumps({"team": "qa"})},
        files={"file": ("doc.md", b"service level objective is 99.9%", "text/markdown")},
    )
    assert create_resp.status_code == 201
    document_id = create_resp.json()["id"]

    index_resp = client.post(
        f"/documents/{document_id}/index",
        json={"embedding_model": "deterministic-local-v1", "chunk_size": 128, "chunk_overlap": 16},
    )
    assert index_resp.status_code == 200
    assert index_resp.json()["chunk_count"] >= 1

    chat_resp = client.post(
        "/chat/query",
        json={
            "query": "service level objective is 99.9%",
            "top_k": 5,
            "score_threshold": 0.1,
            "embedding_model": "deterministic-local-v1",
        },
    )
    assert chat_resp.status_code == 200
    payload = chat_resp.json()
    assert "citations" in payload
    assert isinstance(payload["citations"], list)
    assert len(payload["citations"]) >= 1
    assert payload["citations"][0]["span"]["start_char"] >= 0


@pytest.mark.integration
def test_chat_abstain_when_threshold_too_high(client) -> None:
    create_resp = client.post(
        "/documents",
        data={"title": "Doc API 2"},
        files={"file": ("doc2.txt", b"alpha beta gamma", "text/plain")},
    )
    document_id = create_resp.json()["id"]
    client.post(
        f"/documents/{document_id}/index",
        json={"embedding_model": "deterministic-local-v1", "chunk_size": 64, "chunk_overlap": 8},
    )

    chat_resp = client.post(
        "/chat/query",
        json={
            "query": "completely unrelated question",
            "top_k": 3,
            "score_threshold": 0.99,
            "embedding_model": "deterministic-local-v1",
        },
    )
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["abstained"] is True
    assert body["citations"] == []


@pytest.mark.integration
def test_chat_query_hits_indexed_chinese_term(client) -> None:
    create_resp = client.post(
        "/documents",
        data={"title": "证券术语"},
        files={"file": ("terms.md", "信用账户用于融资融券交易".encode("utf-8"), "text/markdown")},
    )
    assert create_resp.status_code == 201
    document_id = create_resp.json()["id"]

    index_resp = client.post(
        f"/documents/{document_id}/index",
        json={"embedding_model": "deterministic-local-v1", "chunk_size": 128, "chunk_overlap": 16},
    )
    assert index_resp.status_code == 200

    chat_resp = client.post(
        "/chat/query",
        json={
            "query": "信用账户",
            "top_k": 5,
            "score_threshold": 0.8,
            "embedding_model": "deterministic-local-v1",
        },
    )
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["abstained"] is False
    assert len(body["citations"]) >= 1
    assert "信用账户" in body["citations"][0]["quote"]
