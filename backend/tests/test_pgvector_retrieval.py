import pytest

from app.core.config import get_settings
from app.indexing.chunker import SlidingWindowChunker
from app.indexing.embedder import DeterministicEmbedder
from app.indexing.pgvector_index import PgVectorIndex
from app.indexing.service import DocumentIndexingService
from app.ingestion.service import SimpleDocumentIngestionService
from app.retrieval.repository import RetrievalRepository
from app.retrieval.service import PgVectorRetriever


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pgvector_topk_retrieval(db_session) -> None:
    settings = get_settings()

    ingestion = SimpleDocumentIngestionService(db_session)
    document = ingestion.create_document(
        title="Product Policy",
        filename="policy.txt",
        mime_type="text/plain",
        content_bytes=b"warranty period is 12 months for product x",
        metadata={},
        request_id="req-1",
        trace_id="trace-1",
    )

    chunker = SlidingWindowChunker(chunk_size=128, chunk_overlap=16)
    embedder = DeterministicEmbedder(dimension=settings.vector_dim)
    vector_index = PgVectorIndex(db=db_session, settings=settings)
    indexing = DocumentIndexingService(
        db=db_session,
        chunker=chunker,
        embedder=embedder,
        vector_index=vector_index,
        settings=settings,
    )

    await indexing.index_document(
        document_id=document.id,
        embedding_model=settings.default_embedding_model,
        request_id="req-2",
        timeout_seconds=settings.request_timeout_seconds,
    )

    retriever = PgVectorRetriever(
        embedder=embedder,
        repository=RetrievalRepository(vector_index=vector_index),
        settings=settings,
    )

    results = await retriever.retrieve(
        query="warranty period is 12 months for product x",
        top_k=3,
        score_threshold=0.1,
        model=settings.default_embedding_model,
    )

    assert len(results) >= 1
    assert results[0].chunk.document_id == document.id
    assert results[0].score >= 0.1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retrieval_uses_lexical_fallback_when_vector_empty(db_session) -> None:
    settings = get_settings()

    ingestion = SimpleDocumentIngestionService(db_session)
    document = ingestion.create_document(
        title="证券行业术语",
        filename="terms.md",
        mime_type="text/markdown",
        content_bytes="信用账户用于融资融券交易".encode("utf-8"),
        metadata={},
        request_id="req-cn-1",
        trace_id="trace-cn-1",
    )

    chunker = SlidingWindowChunker(chunk_size=128, chunk_overlap=16)
    embedder = DeterministicEmbedder(dimension=settings.vector_dim)
    vector_index = PgVectorIndex(db=db_session, settings=settings)
    indexing = DocumentIndexingService(
        db=db_session,
        chunker=chunker,
        embedder=embedder,
        vector_index=vector_index,
        settings=settings,
    )

    await indexing.index_document(
        document_id=document.id,
        embedding_model=settings.default_embedding_model,
        request_id="req-cn-2",
        timeout_seconds=settings.request_timeout_seconds,
    )

    retriever = PgVectorRetriever(
        embedder=embedder,
        repository=RetrievalRepository(vector_index=vector_index, db=db_session),
        settings=settings,
    )

    results = await retriever.retrieve(
        query="信用账户",
        top_k=3,
        score_threshold=0.8,
        model=settings.default_embedding_model,
    )

    assert len(results) >= 1
    assert results[0].chunk.document_id == document.id
    assert "信用账户" in results[0].chunk.content
    assert results[0].score >= 0.8
