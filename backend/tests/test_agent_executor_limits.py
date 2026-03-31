from __future__ import annotations

import uuid

import pytest

from app.agent.executor import FiniteStateAgentExecutor
from app.agent.state_machine import AgentState
from app.core.config import Settings
from app.db.models import AgentTrace, ChatSession
from app.domain.interfaces import ChunkRecord, ScoredChunk
from app.retrieval.reranker import BasicReranker
from app.services.answer import ThresholdAnswerGenerator
from app.services.citation import BasicCitationAssembler


class EmptyRetriever:
    async def retrieve(self, *, query: str, top_k: int, score_threshold: float, model: str):
        _ = (query, top_k, score_threshold, model)
        return []


class SingleResultRetriever:
    async def retrieve(self, *, query: str, top_k: int, score_threshold: float, model: str):
        _ = (top_k, score_threshold, model)
        return [
            ScoredChunk(
                chunk=ChunkRecord(
                    chunk_id=uuid.uuid4(),
                    document_id=uuid.uuid4(),
                    document_version_id=uuid.uuid4(),
                    content=f"{query} evidence",
                    chunk_index=0,
                    start_char=0,
                    end_char=len(query) + 9,
                    metadata={},
                ),
                score=0.95,
                distance=0.05,
            )
        ]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_max_steps_control(db_session) -> None:
    settings = Settings(agent_max_steps=4, agent_max_rewrites=2)
    session = ChatSession(id=uuid.uuid4(), title="t", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=EmptyRetriever(),
        reranker=BasicReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=ThresholdAnswerGenerator(min_citations=1, min_score=0.3),
    )

    result = await executor.run(
        session_id=session.id,
        query="credit account",
        top_k=5,
        score_threshold=0.25,
        embedding_model="deterministic-local-v1",
        request_id="req-max-steps",
        trace_id="trace-max-steps",
    )

    assert result.final_state == AgentState.FAILED
    assert result.answer.abstained is True
    assert result.answer.reason == "max_steps_exceeded"
    assert any(step.action == "guard:max_steps" for step in result.steps)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_rewrite_limit_control(db_session) -> None:
    settings = Settings(agent_max_steps=12, agent_max_rewrites=1)
    session = ChatSession(id=uuid.uuid4(), title="t", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=EmptyRetriever(),
        reranker=BasicReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=ThresholdAnswerGenerator(min_citations=1, min_score=0.3),
    )

    result = await executor.run(
        session_id=session.id,
        query="credit account",
        top_k=5,
        score_threshold=0.25,
        embedding_model="deterministic-local-v1",
        request_id="req-rewrite-limit",
        trace_id="trace-rewrite-limit",
    )

    assert result.final_state == AgentState.ABSTAIN
    trace = db_session.get(AgentTrace, result.trace_db_id)
    assert trace is not None
    assert trace.meta["rewrite_count"] == 1
    rewrite_steps = [step for step in result.steps if step.state == AgentState.REWRITE_QUERY]
    assert len(rewrite_steps) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_no_evidence_abstain(db_session) -> None:
    settings = Settings(agent_max_steps=10, agent_max_rewrites=0)
    session = ChatSession(id=uuid.uuid4(), title="t", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=EmptyRetriever(),
        reranker=BasicReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=ThresholdAnswerGenerator(min_citations=1, min_score=0.3),
    )

    result = await executor.run(
        session_id=session.id,
        query="unknown term",
        top_k=3,
        score_threshold=0.25,
        embedding_model="deterministic-local-v1",
        request_id="req-no-evidence",
        trace_id="trace-no-evidence",
    )

    assert result.final_state == AgentState.ABSTAIN
    assert result.answer.abstained is True
    assert result.answer.reason in {"no_retrieved_evidence", "insufficient_result_count", "insufficient_result_score"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_happy_path_to_complete(db_session) -> None:
    settings = Settings(agent_max_steps=10, agent_max_rewrites=0)
    session = ChatSession(id=uuid.uuid4(), title="t", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=SingleResultRetriever(),
        reranker=BasicReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=ThresholdAnswerGenerator(min_citations=1, min_score=0.3),
    )

    result = await executor.run(
        session_id=session.id,
        query="slo",
        top_k=3,
        score_threshold=0.1,
        embedding_model="deterministic-local-v1",
        request_id="req-happy",
        trace_id="trace-happy",
    )

    assert result.final_state == AgentState.COMPLETE
    assert result.answer.abstained is False
    assert len(result.citations) >= 1
