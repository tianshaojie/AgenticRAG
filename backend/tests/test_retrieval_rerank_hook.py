from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.errors import DependencyAppError
from app.domain.interfaces import ChunkRecord, ScoredChunk
from app.reranker.interfaces import RerankRequest, RerankResponse, RerankedItem, RerankerProvider
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.reranker import ProviderBackedReranker
from app.services.citation import BasicCitationAssembler


class StaticRerankerProvider(RerankerProvider):
    async def rerank(self, *, request: RerankRequest) -> RerankResponse:
        return RerankResponse(
            items=[
                RerankedItem(
                    candidate_id=request.candidates[1].candidate_id,
                    rank=1,
                    original_index=1,
                    score=0.98,
                ),
                RerankedItem(
                    candidate_id=request.candidates[0].candidate_id,
                    rank=2,
                    original_index=0,
                    score=0.91,
                ),
            ],
            model="mock-reranker-v1",
        )


class FailingRerankerProvider(RerankerProvider):
    async def rerank(self, *, request: RerankRequest) -> RerankResponse:
        _ = request
        raise DependencyAppError(code="reranker_upstream_server_error", message="upstream failed")


class FixedRetriever:
    def __init__(self, rows: list[ScoredChunk]) -> None:
        self._rows = rows

    async def retrieve(self, *, query: str, top_k: int, score_threshold: float, model: str) -> list[ScoredChunk]:
        _ = (query, score_threshold, model)
        return self._rows[:top_k]


def _chunk(candidate_id: str, content: str, score: float) -> ScoredChunk:
    return ScoredChunk(
        chunk=ChunkRecord(
            chunk_id=uuid4(),
            document_id=uuid4(),
            document_version_id=uuid4(),
            content=content,
            chunk_index=0,
            start_char=0,
            end_char=len(content),
            metadata={"candidate_id": candidate_id},
        ),
        score=score,
        distance=1.0 - score,
    )


@pytest.mark.asyncio
async def test_provider_backed_reranker_reorders_and_preserves_identity() -> None:
    rows = [
        _chunk("c1", "机器学习文档", 0.7),
        _chunk("c2", "banana", 0.6),
        _chunk("c3", "fruit", 0.5),
    ]

    reranker = ProviderBackedReranker(
        provider=StaticRerankerProvider(),
        enable_reranking=True,
        model="qwen3-reranker-8b",
        timeout_seconds=5,
        default_top_n=2,
    )

    reranked = await reranker.rerank(query="机器学习", candidates=rows, top_n=2)

    original_ids = {str(item.chunk.chunk_id) for item in rows}
    reranked_ids = [str(item.chunk.chunk_id) for item in reranked]
    assert len(reranked) == 2
    assert set(reranked_ids).issubset(original_ids)
    assert reranked[0].chunk.chunk_id == rows[1].chunk.chunk_id
    assert reranked[1].chunk.chunk_id == rows[0].chunk.chunk_id


@pytest.mark.asyncio
async def test_provider_backed_reranker_fallbacks_to_retrieval_order_on_failure() -> None:
    rows = [
        _chunk("c1", "doc-1", 0.9),
        _chunk("c2", "doc-2", 0.8),
        _chunk("c3", "doc-3", 0.7),
    ]

    reranker = ProviderBackedReranker(
        provider=FailingRerankerProvider(),
        enable_reranking=True,
        model="qwen3-reranker-8b",
        timeout_seconds=5,
        default_top_n=2,
    )

    reranked = await reranker.rerank(query="test", candidates=rows, top_n=2)

    assert [item.chunk.chunk_id for item in reranked] == [rows[0].chunk.chunk_id, rows[1].chunk.chunk_id]


@pytest.mark.asyncio
async def test_retrieval_pipeline_optional_rerank_hook_can_be_disabled() -> None:
    rows = [
        _chunk("c1", "doc-1", 0.9),
        _chunk("c2", "doc-2", 0.8),
    ]

    reranker = ProviderBackedReranker(
        provider=StaticRerankerProvider(),
        enable_reranking=True,
        model="qwen3-reranker-8b",
        timeout_seconds=5,
        default_top_n=2,
    )
    pipeline = RetrievalPipeline(
        retriever=FixedRetriever(rows),
        reranker=reranker,
        citation_assembler=BasicCitationAssembler(),
        enable_reranking=False,
    )

    ranked, citations = await pipeline.run(
        query="test",
        top_k=2,
        score_threshold=0.1,
        model="deterministic-local-v1",
        rerank_k=2,
    )

    assert [item.chunk.chunk_id for item in ranked] == [rows[0].chunk.chunk_id, rows[1].chunk.chunk_id]
    assert len(citations) == 2
