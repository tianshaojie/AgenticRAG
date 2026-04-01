from __future__ import annotations

import uuid

import pytest

from app.db.models import Document, DocumentChunk, DocumentVersion
from app.domain.enums import DocumentStatus
from app.retrieval.route_retrievers import ApiRouteRetriever, SqlRouteRetriever


def _seed_document_chunk(*, db_session, title: str, content: str) -> DocumentChunk:
    document = Document(
        id=uuid.uuid4(),
        title=title,
        source_uri=f"seed://{title}",
        mime_type="text/plain",
        status=DocumentStatus.INDEXED,
        meta={},
    )
    db_session.add(document)
    db_session.flush()

    version = DocumentVersion(
        id=uuid.uuid4(),
        document_id=document.id,
        version_number=1,
        content_sha256="seed-hash",
        content_text=content,
        content_uri=None,
        size_bytes=len(content.encode("utf-8")),
        meta={},
    )
    db_session.add(version)
    db_session.flush()

    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=document.id,
        document_version_id=version.id,
        chunk_index=0,
        content=content,
        token_count=None,
        start_char=0,
        end_char=len(content),
        meta={},
    )
    db_session.add(chunk)
    db_session.commit()
    return chunk


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sql_route_retriever_returns_scored_chunks(db_session) -> None:
    seeded = _seed_document_chunk(
        db_session=db_session,
        title="sql-policy",
        content="风控规则要求用户完成风险测评并通过适当性校验。",
    )
    retriever = SqlRouteRetriever(db=db_session)

    results = await retriever.retrieve(
        query="sql: select 风险测评 from policy",
        top_k=5,
        score_threshold=0.1,
        model="deterministic-local-v1",
    )

    assert len(results) >= 1
    assert results[0].chunk.chunk_id == seeded.id
    assert results[0].chunk.metadata["retrieval_source"] == "sql_route"
    assert results[0].chunk.metadata["route"] == "sql"
    assert results[0].chunk.metadata["route_provider"] == "sql_lexical"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_route_retriever_returns_scored_chunks(db_session) -> None:
    seeded = _seed_document_chunk(
        db_session=db_session,
        title="api-policy",
        content="信用账户支持查询融资融券状态。",
    )
    retriever = ApiRouteRetriever(db=db_session)

    results = await retriever.retrieve(
        query="api: 信用账户",
        top_k=5,
        score_threshold=0.1,
        model="deterministic-local-v1",
    )

    assert len(results) >= 1
    assert results[0].chunk.chunk_id == seeded.id
    assert results[0].chunk.metadata["retrieval_source"] == "api_route"
    assert results[0].chunk.metadata["route"] == "api"
    assert results[0].chunk.metadata["route_provider"] == "api_lexical"
