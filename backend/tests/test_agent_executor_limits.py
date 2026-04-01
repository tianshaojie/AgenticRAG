from __future__ import annotations

import uuid

import pytest

from app.agent.executor import FiniteStateAgentExecutor
from app.agent.state_machine import AgentState
from app.core.config import Settings
from app.db.models import AgentTrace, ChatSession
from app.domain.interfaces import ChunkRecord, GeneratedAnswer, ScoredChunk
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


class StagnantScoreRetriever:
    def __init__(self, *, score: float = 0.50) -> None:
        self._score = score

    async def retrieve(self, *, query: str, top_k: int, score_threshold: float, model: str):
        _ = (top_k, score_threshold, model)
        return [
            ScoredChunk(
                chunk=ChunkRecord(
                    chunk_id=uuid.uuid4(),
                    document_id=uuid.uuid4(),
                    document_version_id=uuid.uuid4(),
                    content=f"{query} stagnant evidence",
                    chunk_index=0,
                    start_char=0,
                    end_char=len(query) + 18,
                    metadata={},
                ),
                score=self._score,
                distance=1 - self._score,
            )
        ]


class MediumScoreRetriever:
    async def retrieve(self, *, query: str, top_k: int, score_threshold: float, model: str):
        _ = (query, top_k, score_threshold, model)
        return [
            ScoredChunk(
                chunk=ChunkRecord(
                    chunk_id=uuid.uuid4(),
                    document_id=uuid.uuid4(),
                    document_version_id=uuid.uuid4(),
                    content="medium confidence evidence",
                    chunk_index=0,
                    start_char=0,
                    end_char=26,
                    metadata={},
                ),
                score=0.90,
                distance=0.10,
            )
        ]


class SqlOnlyRetriever:
    async def retrieve(self, *, query: str, top_k: int, score_threshold: float, model: str):
        _ = (query, top_k, score_threshold, model)
        text = "sql route evidence: 风险测评和适当性要求"
        return [
            ScoredChunk(
                chunk=ChunkRecord(
                    chunk_id=uuid.uuid4(),
                    document_id=uuid.uuid4(),
                    document_version_id=uuid.uuid4(),
                    content=text,
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata={"retrieval_source": "sql_route", "route": "sql"},
                ),
                score=0.93,
                distance=0.07,
            )
        ]


class ApiOnlyRetriever:
    async def retrieve(self, *, query: str, top_k: int, score_threshold: float, model: str):
        _ = (query, top_k, score_threshold, model)
        text = "api route evidence: 信用账户支持查询"
        return [
            ScoredChunk(
                chunk=ChunkRecord(
                    chunk_id=uuid.uuid4(),
                    document_id=uuid.uuid4(),
                    document_version_id=uuid.uuid4(),
                    content=text,
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata={"retrieval_source": "api_route", "route": "api"},
                ),
                score=0.92,
                distance=0.08,
            )
        ]


class NonCitedAnswerGenerator:
    async def generate(self, *, query: str, citations, request_id: str = "unknown", trace_id: str = "unknown"):
        _ = (query, citations, request_id, trace_id)
        return GeneratedAnswer(
            text="This answer is not backed by citations.",
            citations=[],
            abstained=False,
            reason=None,
        )


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
async def test_agent_stops_on_retrieval_stagnation(db_session) -> None:
    settings = Settings(
        agent_max_steps=12,
        agent_max_rewrites=4,
        evidence_min_score=0.8,
        agent_retrieval_stagnation_limit=1,
        agent_retrieval_min_score_gain=0.05,
    )
    session = ChatSession(id=uuid.uuid4(), title="stagnation", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=StagnantScoreRetriever(score=0.5),
        reranker=BasicReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=ThresholdAnswerGenerator(min_citations=1, min_score=0.3),
    )

    result = await executor.run(
        session_id=session.id,
        query="信用账户",
        top_k=3,
        score_threshold=0.1,
        embedding_model="deterministic-local-v1",
        request_id="req-stagnation",
        trace_id="trace-stagnation",
    )

    assert result.final_state == AgentState.ABSTAIN
    assert result.answer.abstained is True
    assert result.answer.reason == "retrieval_stagnated"
    eval_step = next(step for step in result.steps if step.state == AgentState.EVALUATE_EVIDENCE)
    assert "retrieval_stagnated" in eval_step.output_summary


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_abstains_when_filter_removes_all_reranked_evidence(db_session) -> None:
    settings = Settings(
        agent_max_steps=12,
        agent_max_rewrites=0,
        evidence_min_score=0.30,
        agent_filter_min_score=0.95,
    )
    session = ChatSession(id=uuid.uuid4(), title="filter-empty", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=MediumScoreRetriever(),
        reranker=BasicReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=ThresholdAnswerGenerator(min_citations=1, min_score=0.3),
    )

    result = await executor.run(
        session_id=session.id,
        query="信用账户",
        top_k=3,
        score_threshold=0.1,
        embedding_model="deterministic-local-v1",
        request_id="req-filter-empty",
        trace_id="trace-filter-empty",
    )

    assert result.final_state == AgentState.ABSTAIN
    assert result.answer.abstained is True
    assert result.answer.reason == "filtered_evidence_empty"
    rerank_step = next(step for step in result.steps if step.state == AgentState.RERANK)
    assert "filtered=0" in rerank_step.output_summary
    assert rerank_step.fallback is False


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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_uses_sql_route_retriever_when_available(db_session) -> None:
    settings = Settings(
        agent_max_steps=12,
        agent_max_rewrites=0,
        agent_available_routes=["pgvector", "sql", "api"],
    )
    session = ChatSession(id=uuid.uuid4(), title="sql-route", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=EmptyRetriever(),
        reranker=BasicReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=ThresholdAnswerGenerator(min_citations=1, min_score=0.3),
        route_retrievers={
            "pgvector": EmptyRetriever(),
            "sql": SqlOnlyRetriever(),
            "api": ApiOnlyRetriever(),
        },
    )

    result = await executor.run(
        session_id=session.id,
        query="sql: 风险测评 适当性",
        top_k=3,
        score_threshold=0.1,
        embedding_model="deterministic-local-v1",
        request_id="req-sql-route",
        trace_id="trace-sql-route",
    )

    assert result.final_state == AgentState.COMPLETE
    assert result.answer.abstained is False
    route_step = next(step for step in result.steps if step.state == AgentState.ROUTE)
    retrieve_step = next(step for step in result.steps if step.state == AgentState.RETRIEVE)
    assert "selected=sql" in route_step.output_summary
    assert retrieve_step.output_summary.startswith("retrieved=1")

    trace = db_session.get(AgentTrace, result.trace_db_id)
    assert trace is not None
    persisted_route_step = next(row for row in trace.steps if row.state == AgentState.ROUTE.value)
    persisted_retrieve_step = next(row for row in trace.steps if row.state == AgentState.RETRIEVE.value)
    assert persisted_route_step.output_payload["selected_route"] == "sql"
    assert persisted_route_step.output_payload["route_retriever"] == "SqlOnlyRetriever"
    assert persisted_route_step.output_payload["route_provider"] == "SqlOnlyRetriever"
    assert persisted_retrieve_step.output_payload["route_retriever"] == "SqlOnlyRetriever"
    assert persisted_retrieve_step.output_payload["route_provider"] == "SqlOnlyRetriever"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_uses_api_route_retriever_when_available(db_session) -> None:
    settings = Settings(
        agent_max_steps=12,
        agent_max_rewrites=0,
        agent_available_routes=["pgvector", "sql", "api"],
    )
    session = ChatSession(id=uuid.uuid4(), title="api-route", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=EmptyRetriever(),
        reranker=BasicReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=ThresholdAnswerGenerator(min_citations=1, min_score=0.3),
        route_retrievers={
            "pgvector": EmptyRetriever(),
            "sql": SqlOnlyRetriever(),
            "api": ApiOnlyRetriever(),
        },
    )

    result = await executor.run(
        session_id=session.id,
        query="api: 信用账户",
        top_k=3,
        score_threshold=0.1,
        embedding_model="deterministic-local-v1",
        request_id="req-api-route",
        trace_id="trace-api-route",
    )

    assert result.final_state == AgentState.COMPLETE
    assert result.answer.abstained is False
    trace = db_session.get(AgentTrace, result.trace_db_id)
    assert trace is not None
    persisted_route_step = next(row for row in trace.steps if row.state == AgentState.ROUTE.value)
    persisted_retrieve_step = next(row for row in trace.steps if row.state == AgentState.RETRIEVE.value)
    assert persisted_route_step.output_payload["selected_route"] == "api"
    assert persisted_route_step.output_payload["route_retriever"] == "ApiOnlyRetriever"
    assert persisted_route_step.output_payload["route_provider"] == "ApiOnlyRetriever"
    assert persisted_retrieve_step.output_payload["route_retriever"] == "ApiOnlyRetriever"
    assert persisted_retrieve_step.output_payload["route_provider"] == "ApiOnlyRetriever"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_route_retriever_missing_fallbacks_to_pgvector(db_session) -> None:
    settings = Settings(
        agent_max_steps=12,
        agent_max_rewrites=0,
        agent_available_routes=["pgvector", "sql"],
    )
    session = ChatSession(id=uuid.uuid4(), title="route-fallback", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=SingleResultRetriever(),
        reranker=BasicReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=ThresholdAnswerGenerator(min_citations=1, min_score=0.3),
        route_retrievers={"pgvector": SingleResultRetriever()},
    )

    result = await executor.run(
        session_id=session.id,
        query="sql: select count(*) from account",
        top_k=3,
        score_threshold=0.1,
        embedding_model="deterministic-local-v1",
        request_id="req-route-missing-fallback",
        trace_id="trace-route-missing-fallback",
    )

    assert result.final_state == AgentState.COMPLETE
    trace = db_session.get(AgentTrace, result.trace_db_id)
    assert trace is not None
    persisted_route_step = next(row for row in trace.steps if row.state == AgentState.ROUTE.value)
    persisted_retrieve_step = next(row for row in trace.steps if row.state == AgentState.RETRIEVE.value)
    assert persisted_route_step.output_payload["selected_route"] == "pgvector"
    assert persisted_route_step.output_payload["fallback"] is True
    assert "missing_fallback_pgvector" in persisted_route_step.output_payload["route_reason"]
    assert persisted_retrieve_step.output_payload["route_retriever"] == "SingleResultRetriever"
    assert persisted_retrieve_step.output_payload["route_provider"] == "SingleResultRetriever"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_route_state_records_fallback_for_unavailable_tool(db_session) -> None:
    settings = Settings(
        agent_max_steps=12,
        agent_max_rewrites=0,
        agent_available_routes=["pgvector"],
    )
    session = ChatSession(id=uuid.uuid4(), title="routing", meta={})
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
        query="sql: count credit accounts by month",
        top_k=3,
        score_threshold=0.1,
        embedding_model="deterministic-local-v1",
        request_id="req-route-fallback",
        trace_id="trace-route-fallback",
    )

    assert result.final_state == AgentState.COMPLETE
    route_step = next(step for step in result.steps if step.state == AgentState.ROUTE)
    assert route_step.fallback is True

    trace = db_session.get(AgentTrace, result.trace_db_id)
    assert trace is not None
    persisted_route_step = next(row for row in trace.steps if row.state == AgentState.ROUTE.value)
    assert persisted_route_step.output_payload["selected_route"] == "pgvector"
    assert persisted_route_step.output_payload["preferred_route"] == "sql"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_query_analysis_and_route_payload_are_persisted(db_session) -> None:
    settings = Settings(agent_max_steps=12, agent_max_rewrites=0)
    session = ChatSession(id=uuid.uuid4(), title="analysis", meta={})
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
        query="retrival 信用帐户",
        top_k=3,
        score_threshold=0.1,
        embedding_model="deterministic-local-v1",
        request_id="req-analysis-route",
        trace_id="trace-analysis-route",
    )

    assert result.final_state == AgentState.COMPLETE
    analysis_step = next(step for step in result.steps if step.state == AgentState.ANALYZE_QUERY)
    route_step = next(step for step in result.steps if step.state == AgentState.ROUTE)
    assert "intent=knowledge_lookup" in analysis_step.output_summary
    assert "selected=pgvector" in route_step.output_summary

    trace = db_session.get(AgentTrace, result.trace_db_id)
    assert trace is not None
    persisted_analysis_step = next(row for row in trace.steps if row.state == AgentState.ANALYZE_QUERY.value)
    persisted_route_step = next(row for row in trace.steps if row.state == AgentState.ROUTE.value)
    assert persisted_analysis_step.output_payload["corrected_query"] == "retrieval 信用账户"
    assert persisted_analysis_step.output_payload["intent"] == "knowledge_lookup"
    assert persisted_route_step.output_payload["analysis_intent"] == "knowledge_lookup"
    assert persisted_route_step.output_payload["selected_route"] == "pgvector"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_critique_forces_abstain_when_answer_has_no_citations(db_session) -> None:
    settings = Settings(agent_max_steps=12, agent_max_rewrites=0)
    session = ChatSession(id=uuid.uuid4(), title="critique", meta={})
    db_session.add(session)
    db_session.flush()

    executor = FiniteStateAgentExecutor(
        db=db_session,
        settings=settings,
        retriever=SingleResultRetriever(),
        reranker=BasicReranker(),
        citation_assembler=BasicCitationAssembler(),
        answer_generator=NonCitedAnswerGenerator(),
    )

    result = await executor.run(
        session_id=session.id,
        query="信用账户",
        top_k=3,
        score_threshold=0.1,
        embedding_model="deterministic-local-v1",
        request_id="req-critique-abstain",
        trace_id="trace-critique-abstain",
    )

    assert result.final_state == AgentState.ABSTAIN
    assert result.answer.abstained is True
    assert result.answer.reason == "critique_missing_citations"
    critique_step = next(step for step in result.steps if step.state == AgentState.CRITIQUE)
    assert critique_step.fallback is True
