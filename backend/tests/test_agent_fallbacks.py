from __future__ import annotations

import uuid

import pytest

from app.agent.executor import FiniteStateAgentExecutor
from app.agent.state_machine import AgentState
from app.core.config import Settings
from app.core.errors import DependencyAppError, TimeoutAppError
from app.db.models import ChatSession
from app.domain.interfaces import ChunkRecord, ScoredChunk
from app.services.answer import ThresholdAnswerGenerator
from app.services.citation import BasicCitationAssembler


def _scored_chunk(content: str = "evidence") -> ScoredChunk:
    return ScoredChunk(
        chunk=ChunkRecord(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            content=content,
            chunk_index=0,
            start_char=0,
            end_char=len(content),
            metadata={},
        ),
        score=0.9,
        distance=0.1,
    )


class FailingRetriever:
    async def retrieve(self, *, query: str, top_k: int, score_threshold: float, model: str):
        _ = (query, top_k, score_threshold, model)
        raise DependencyAppError(code="retrieval_unavailable", message="retriever unavailable")


class SingleRetriever:
    async def retrieve(self, *, query: str, top_k: int, score_threshold: float, model: str):
        _ = (query, top_k, score_threshold, model)
        return [_scored_chunk(query)]


class FailingReranker:
    async def rerank(
        self,
        *,
        query: str,
        candidates: list[ScoredChunk],
        top_n: int,
        request_id: str = "unknown",
        trace_id: str = "unknown",
    ):
        _ = (query, candidates, top_n, request_id, trace_id)
        raise TimeoutAppError(code="rerank_timeout", message="rerank timeout")


class PassReranker:
    async def rerank(
        self,
        *,
        query: str,
        candidates: list[ScoredChunk],
        top_n: int,
        request_id: str = "unknown",
        trace_id: str = "unknown",
    ):
        _ = query, request_id, trace_id
        return candidates[:top_n]


class FailingAnswerGenerator:
    async def generate(self, *, query: str, citations, request_id: str = "unknown", trace_id: str = "unknown"):
        _ = (query, citations, request_id, trace_id)
        raise DependencyAppError(code="generation_unavailable", message="generator unavailable")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retrieval_failure_fallback_to_abstain(db_session) -> None:
    settings = Settings(agent_max_steps=8, agent_max_rewrites=1)
    session = ChatSession(id=uuid.uuid4(), title="fallback", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=FailingRetriever(),
        reranker=PassReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=ThresholdAnswerGenerator(min_citations=1, min_score=0.3),
    )

    result = await executor.run(
        session_id=session.id,
        query="credit account",
        top_k=3,
        score_threshold=0.25,
        embedding_model="deterministic-local-v1",
        request_id="req-fallback-retrieve",
        trace_id="trace-fallback-retrieve",
    )

    assert result.final_state == AgentState.ABSTAIN
    assert result.answer.abstained is True
    assert result.answer.reason == "retrieval_failure_fallback"
    retrieve_step = next(step for step in result.steps if step.state == AgentState.RETRIEVE)
    assert retrieve_step.fallback is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rerank_failure_fallback_to_candidates(db_session) -> None:
    settings = Settings(agent_max_steps=8, agent_max_rewrites=0)
    session = ChatSession(id=uuid.uuid4(), title="fallback", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=SingleRetriever(),
        reranker=FailingReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=ThresholdAnswerGenerator(min_citations=1, min_score=0.3),
    )

    result = await executor.run(
        session_id=session.id,
        query="credit account",
        top_k=3,
        score_threshold=0.25,
        embedding_model="deterministic-local-v1",
        request_id="req-fallback-rerank",
        trace_id="trace-fallback-rerank",
    )

    assert result.final_state == AgentState.COMPLETE
    assert result.answer.abstained is False
    rerank_step = next(step for step in result.steps if step.state == AgentState.RERANK)
    assert rerank_step.fallback is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generation_failure_fallback_to_abstain(db_session) -> None:
    settings = Settings(agent_max_steps=8, agent_max_rewrites=0)
    session = ChatSession(id=uuid.uuid4(), title="fallback", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=SingleRetriever(),
        reranker=PassReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=FailingAnswerGenerator(),
    )

    result = await executor.run(
        session_id=session.id,
        query="credit account",
        top_k=3,
        score_threshold=0.25,
        embedding_model="deterministic-local-v1",
        request_id="req-fallback-generate",
        trace_id="trace-fallback-generate",
    )

    assert result.final_state == AgentState.COMPLETE
    assert result.answer.abstained is True
    assert result.answer.reason == "generation_failure_fallback"
    generate_step = next(step for step in result.steps if step.state == AgentState.GENERATE_ANSWER)
    assert generate_step.fallback is True
