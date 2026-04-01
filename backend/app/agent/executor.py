from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.agent.evidence import DefaultEvidenceSufficiencyJudge
from app.agent.filtering import DefaultEvidenceFilter
from app.agent.interfaces import (
    EvidenceFilter,
    EvidenceSufficiencyJudge,
    QueryAnalyzer,
    QueryRewriteStrategy,
    QueryRouter,
)
from app.agent.models import (
    AgentExecutionResult,
    AgentStepModel,
    EvidenceAssessment,
    QueryAnalysis,
    RouteDecision,
)
from app.agent.policy import DefaultAgentPolicy
from app.agent.query_analysis import DeterministicQueryAnalyzer
from app.agent.rewrite import DefaultQueryRewriteStrategy
from app.agent.routing import HeuristicQueryRouter
from app.agent.state_machine import TERMINAL_STATES, AgentState
from app.core.config import Settings
from app.core.errors import AppError
from app.core.resilience import ResiliencePolicy, call_with_resilience
from app.db.models import AgentTrace, AgentTraceStep
from app.domain.enums import StepStatus, TraceStatus
from app.domain.interfaces import (
    AnswerGenerator,
    CitationAssembler,
    GeneratedAnswer,
    Reranker,
    Retriever,
    ScoredChunk,
)
from app.retrieval.route_provider_factory import build_route_retrievers


@dataclass(slots=True)
class _RuntimeContext:
    original_query: str
    current_query: str
    top_k: int
    score_threshold: float
    embedding_model: str
    rewrite_count: int = 0
    analysis: QueryAnalysis | None = None
    route_decision: RouteDecision | None = None
    need_retrieval: bool = True
    route_preferred: str = "pgvector"
    route_selected: str = "pgvector"
    route_retriever_name: str = "unknown"
    route_provider_name: str = "unknown"
    route_reason: str = "default_pgvector"
    route_failed: bool = False
    route_fallback_to_abstain: bool = False
    route_fallback_used: bool = False
    candidates: list[ScoredChunk] | None = None
    reranked: list[ScoredChunk] | None = None
    assessment: EvidenceAssessment | None = None
    answer: GeneratedAnswer | None = None
    critique_failed: bool = False
    critique_requires_abstain: bool = False
    critique_reason: str | None = None
    fallback_used: bool = False
    failure_reason: str | None = None
    abstain_reason: str | None = None
    retrieve_fallback_to_abstain: bool = False
    last_retrieval_top_score: float | None = None
    retrieval_stagnation_count: int = 0
    retrieval_stagnated: bool = False
    rerank_empty: bool = False


class FiniteStateAgentExecutor:
    def __init__(
        self,
        *,
        db: Session,
        settings: Settings,
        retriever: Retriever,
        reranker: Reranker,
        citation_assembler: CitationAssembler,
        answer_generator: AnswerGenerator,
        policy: DefaultAgentPolicy | None = None,
        query_analyzer: QueryAnalyzer | None = None,
        query_router: QueryRouter | None = None,
        rewrite_strategy: QueryRewriteStrategy | None = None,
        evidence_judge: EvidenceSufficiencyJudge | None = None,
        evidence_filter: EvidenceFilter | None = None,
        route_retrievers: dict[str, Retriever] | None = None,
    ) -> None:
        self._db = db
        self._settings = settings
        self._retriever = retriever
        self._reranker = reranker
        self._citation_assembler = citation_assembler
        self._answer_generator = answer_generator
        self._policy = policy or DefaultAgentPolicy()
        self._query_analyzer = query_analyzer or DeterministicQueryAnalyzer()
        self._query_router = query_router or HeuristicQueryRouter()
        self._rewrite_strategy = rewrite_strategy or DefaultQueryRewriteStrategy()
        self._evidence_filter = evidence_filter or DefaultEvidenceFilter(
            max_chunks_per_document=settings.agent_max_chunks_per_document
        )
        if route_retrievers is None:
            self._route_retrievers = build_route_retrievers(
                settings=settings,
                db=db,
                pgvector_retriever=retriever,
            )
        else:
            self._route_retrievers = {}
            for route_key, route_retriever in route_retrievers.items():
                normalized_route = route_key.strip().lower()
                if not normalized_route:
                    continue
                self._route_retrievers[normalized_route] = route_retriever
        if "pgvector" not in self._route_retrievers:
            self._route_retrievers["pgvector"] = retriever
        self._logger = logging.getLogger("app.agent")
        self._evidence_judge = evidence_judge or DefaultEvidenceSufficiencyJudge(
            min_results=settings.agent_min_evidence_results,
            min_score=settings.evidence_min_score,
            conflict_delta=settings.agent_conflict_score_delta,
        )

    @staticmethod
    def _route_provider_name(route_retriever: Retriever | None) -> str:
        if route_retriever is None:
            return "unknown"
        provider_name = getattr(route_retriever, "provider_name", None)
        if isinstance(provider_name, str) and provider_name.strip():
            return provider_name
        return type(route_retriever).__name__

    @staticmethod
    def _analysis_payload(analysis: QueryAnalysis | None) -> dict[str, Any]:
        if analysis is None:
            return {}
        return {
            "original_query": analysis.original_query[:200],
            "normalized_query": analysis.normalized_query[:200],
            "corrected_query": analysis.corrected_query[:200],
            "expanded_terms": analysis.expanded_terms[:8],
            "intent": analysis.intent,
            "need_retrieval": analysis.need_retrieval,
            "confidence": round(analysis.confidence, 3),
            "reasons": analysis.reasons[:8],
        }

    def _record_step(
        self,
        *,
        trace_id,
        request_id: str,
        query_id: str,
        step_order: int,
        state: AgentState,
        action: str,
        status: StepStatus,
        input_summary: str,
        output_summary: str,
        input_payload: dict,
        output_payload: dict,
        latency_ms: int,
        error_message: str | None = None,
    ) -> AgentStepModel:
        row = AgentTraceStep(
            id=uuid.uuid4(),
            trace_id=trace_id,
            step_order=step_order,
            state=state.value,
            action=action,
            status=status,
            input_payload={"summary": input_summary, **input_payload},
            output_payload={"summary": output_summary, **output_payload},
            latency_ms=latency_ms,
            error_message=error_message,
            created_at=datetime.now(UTC),
        )
        self._db.add(row)
        self._db.flush()

        fallback_used = bool(output_payload.get("fallback", False))
        self._logger.info(
            "agent_step_recorded",
            extra={
                "request_id": request_id,
                "trace_id": str(trace_id),
                "query_id": query_id,
                "agent_state": state.value,
                "latency_ms": latency_ms,
                "fallback_used": fallback_used,
                "operation": action,
            },
        )

        return AgentStepModel(
            step_order=step_order,
            state=state,
            action=action,
            status=status.value,
            input_summary=input_summary,
            output_summary=output_summary,
            latency_ms=latency_ms,
            fallback=fallback_used,
            error_message=error_message,
        )

    async def run(
        self,
        *,
        session_id,
        query: str,
        top_k: int,
        score_threshold: float,
        embedding_model: str,
        request_id: str,
        trace_id: str,
    ) -> AgentExecutionResult:
        trace_row = AgentTrace(
            id=uuid.uuid4(),
            session_id=session_id,
            query_text=query,
            status=TraceStatus.RUNNING,
            start_state=AgentState.INIT.value,
            end_state=None,
            request_id=request_id,
            trace_id=trace_id,
            meta={
                "max_steps": self._settings.agent_max_steps,
                "max_rewrites": self._settings.agent_max_rewrites,
            },
            started_at=datetime.now(UTC),
        )
        self._db.add(trace_row)
        self._db.flush()
        query_id = str(trace_row.id)

        runtime = _RuntimeContext(
            original_query=query,
            current_query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            embedding_model=embedding_model,
        )
        retrieval_policy = ResiliencePolicy(
            timeout_seconds=float(self._settings.retrieval_timeout_seconds),
            max_retries=self._settings.retrieval_retry_attempts,
            backoff_base_ms=self._settings.provider_backoff_base_ms,
            backoff_max_ms=self._settings.provider_backoff_max_ms,
        )
        rerank_policy = ResiliencePolicy(
            timeout_seconds=float(self._settings.rerank_timeout_seconds),
            max_retries=self._settings.rerank_retry_attempts,
            backoff_base_ms=self._settings.provider_backoff_base_ms,
            backoff_max_ms=self._settings.provider_backoff_max_ms,
        )
        generation_policy = ResiliencePolicy(
            timeout_seconds=float(self._settings.generation_timeout_seconds),
            max_retries=self._settings.generation_retry_attempts,
            backoff_base_ms=self._settings.provider_backoff_base_ms,
            backoff_max_ms=self._settings.provider_backoff_max_ms,
        )

        state = AgentState.INIT
        steps: list[AgentStepModel] = []
        step_order = 0

        while True:
            if step_order >= self._settings.agent_max_steps:
                runtime.failure_reason = "max_steps_exceeded"
                state = AgentState.FAILED
                step_order += 1
                steps.append(
                    self._record_step(
                        trace_id=trace_row.id,
                        request_id=request_id,
                        query_id=query_id,
                        step_order=step_order,
                        state=state,
                        action="guard:max_steps",
                        status=StepStatus.FAILED,
                        input_summary=f"max_steps={self._settings.agent_max_steps}",
                        output_summary="forced_failed",
                        input_payload={"step_count": step_order - 1},
                        output_payload={"reason": runtime.failure_reason, "fallback": True},
                        latency_ms=0,
                        error_message=runtime.failure_reason,
                    )
                )
                break

            step_order += 1
            started = time.perf_counter()
            action = ""
            input_summary = ""
            output_summary = ""
            input_payload: dict = {}
            output_payload: dict = {}

            try:
                if state == AgentState.INIT:
                    action = "initialize"
                    input_summary = "initialize runtime"
                    output_summary = f"query_len={len(runtime.current_query.strip())}"
                    input_payload = {"query_preview": runtime.current_query[:120]}
                    output_payload = {"need_retrieval": runtime.need_retrieval}

                elif state == AgentState.ANALYZE_QUERY:
                    action = "analyze_query"
                    input_payload = {"query": runtime.current_query[:200]}
                    runtime.analysis = self._query_analyzer.analyze(
                        query=runtime.current_query,
                        min_query_chars=self._settings.agent_query_min_chars,
                    )
                    runtime.current_query = runtime.analysis.corrected_query
                    runtime.need_retrieval = runtime.analysis.need_retrieval
                    if not runtime.need_retrieval:
                        runtime.abstain_reason = "analysis_skip_retrieval"
                    input_summary = "analyze query intent, normalization, retrieval need"
                    output_summary = (
                        f"intent={runtime.analysis.intent}, "
                        f"need_retrieval={runtime.analysis.need_retrieval}, "
                        f"confidence={runtime.analysis.confidence:.2f}"
                    )
                    output_payload = self._analysis_payload(runtime.analysis)

                elif state == AgentState.ROUTE:
                    action = "route_query"
                    input_summary = "route query to available tools"
                    analysis = runtime.analysis or self._query_analyzer.analyze(
                        query=runtime.current_query,
                        min_query_chars=self._settings.agent_query_min_chars,
                    )
                    runtime.analysis = analysis
                    input_payload = {
                        "query": runtime.current_query[:200],
                        "need_retrieval": runtime.need_retrieval,
                        "analysis": self._analysis_payload(analysis),
                        "available_routes": self._settings.agent_available_routes,
                    }

                    runtime.route_failed = False
                    runtime.route_fallback_to_abstain = False
                    runtime.route_decision = self._query_router.route(
                        analysis=analysis,
                        available_routes=self._settings.agent_available_routes,
                    )
                    runtime.route_preferred = runtime.route_decision.preferred_route
                    runtime.route_selected = runtime.route_decision.selected_route.lower()
                    runtime.route_reason = runtime.route_decision.reason
                    runtime.route_fallback_used = runtime.route_decision.fallback
                    runtime.route_retriever_name = "unknown"
                    runtime.route_provider_name = "unknown"
                    if runtime.route_selected == "abstain":
                        runtime.route_fallback_to_abstain = True
                        runtime.abstain_reason = "route_no_available_tool"
                    elif runtime.route_selected not in self._route_retrievers:
                        if "pgvector" in self._route_retrievers:
                            runtime.route_selected = "pgvector"
                            runtime.route_fallback_used = True
                            runtime.route_reason = (
                                f"{runtime.route_preferred}_route_missing_fallback_pgvector"
                            )
                        else:
                            runtime.route_fallback_to_abstain = True
                            runtime.route_fallback_used = True
                            runtime.abstain_reason = "route_not_implemented"
                            runtime.route_reason = f"{runtime.route_preferred}_route_not_implemented"
                    route_retriever = self._route_retrievers.get(runtime.route_selected)
                    if route_retriever is not None:
                        runtime.route_retriever_name = type(route_retriever).__name__
                        runtime.route_provider_name = self._route_provider_name(route_retriever)
                    runtime.fallback_used = runtime.fallback_used or runtime.route_fallback_used

                    output_summary = (
                        f"preferred={runtime.route_preferred}, selected={runtime.route_selected}, "
                        f"fallback={runtime.route_fallback_used}"
                    )
                    output_payload = {
                        "preferred_route": runtime.route_preferred,
                        "selected_route": runtime.route_selected,
                        "available_routes": runtime.route_decision.available_routes
                        if runtime.route_decision
                        else self._settings.agent_available_routes,
                        "route_reason": runtime.route_reason,
                        "route_confidence": runtime.route_decision.confidence if runtime.route_decision else 0.0,
                        "route_retriever": runtime.route_retriever_name,
                        "route_provider": runtime.route_provider_name,
                        "fallback": runtime.route_fallback_used,
                        "analysis_intent": analysis.intent,
                    }

                elif state == AgentState.RETRIEVE:
                    action = "retrieve"
                    route_retriever = self._route_retrievers.get(runtime.route_selected)
                    if route_retriever is None:
                        route_retriever = self._route_retrievers["pgvector"]
                        runtime.route_selected = "pgvector"
                        runtime.route_retriever_name = type(route_retriever).__name__
                        runtime.route_provider_name = self._route_provider_name(route_retriever)
                        runtime.route_fallback_used = True
                        runtime.fallback_used = True
                        runtime.route_reason = (
                            f"{runtime.route_preferred}_route_missing_fallback_pgvector"
                        )
                    else:
                        runtime.route_retriever_name = type(route_retriever).__name__
                        runtime.route_provider_name = self._route_provider_name(route_retriever)
                    input_summary = f"query={runtime.current_query[:120]}"
                    input_payload = {
                        "query": runtime.current_query[:200],
                        "top_k": runtime.top_k,
                        "score_threshold": runtime.score_threshold,
                        "route_selected": runtime.route_selected,
                        "route_retriever": runtime.route_retriever_name,
                        "route_provider": runtime.route_provider_name,
                    }
                    runtime.retrieve_fallback_to_abstain = False
                    runtime.retrieval_stagnated = False
                    try:
                        runtime.candidates = await call_with_resilience(
                            operation="retrieval",
                            provider_name=runtime.route_provider_name,
                            policy=retrieval_policy,
                            call=lambda route_retriever=route_retriever,
                            query=runtime.current_query,
                            top_k=runtime.top_k,
                            score_threshold=runtime.score_threshold,
                            model=runtime.embedding_model: route_retriever.retrieve(
                                query=query,
                                top_k=top_k,
                                score_threshold=score_threshold,
                                model=model,
                            ),
                            logger=self._logger,
                            request_id=request_id,
                            trace_id=trace_id,
                            query_id=query_id,
                            agent_state=state.value,
                        )
                        fallback_used = any(
                            item.chunk.metadata.get("retrieval_source") == "lexical_fallback"
                            for item in runtime.candidates
                        )
                        runtime.fallback_used = runtime.fallback_used or fallback_used
                        top_score = max((item.score for item in runtime.candidates), default=0.0)
                        previous_top_score = runtime.last_retrieval_top_score
                        score_gain: float | None = None
                        if previous_top_score is None:
                            runtime.retrieval_stagnation_count = 0
                        else:
                            score_gain = top_score - previous_top_score
                            if score_gain < self._settings.agent_retrieval_min_score_gain:
                                runtime.retrieval_stagnation_count += 1
                            else:
                                runtime.retrieval_stagnation_count = 0
                        runtime.last_retrieval_top_score = top_score
                        runtime.retrieval_stagnated = (
                            runtime.rewrite_count > 0
                            and runtime.retrieval_stagnation_count
                            >= self._settings.agent_retrieval_stagnation_limit
                        )
                        output_summary = (
                            f"retrieved={len(runtime.candidates)} top_score={top_score:.3f} "
                            f"stagnated={runtime.retrieval_stagnated}"
                        )
                        output_payload = {
                            "retrieved_count": len(runtime.candidates),
                            "top_score": top_score,
                            "previous_top_score": previous_top_score,
                            "score_gain": score_gain,
                            "stagnation_count": runtime.retrieval_stagnation_count,
                            "retrieval_stagnated": runtime.retrieval_stagnated,
                            "fallback": fallback_used,
                            "route_selected": runtime.route_selected,
                            "route_retriever": runtime.route_retriever_name,
                            "route_provider": runtime.route_provider_name,
                        }
                    except AppError as exc:
                        runtime.candidates = []
                        runtime.fallback_used = True
                        runtime.retrieve_fallback_to_abstain = True
                        runtime.abstain_reason = "retrieval_failure_fallback"
                        output_summary = "retrieval_failed_fallback_to_abstain"
                        output_payload = {
                            "retrieved_count": 0,
                            "top_score": 0.0,
                            "previous_top_score": runtime.last_retrieval_top_score,
                            "score_gain": None,
                            "stagnation_count": runtime.retrieval_stagnation_count,
                            "retrieval_stagnated": runtime.retrieval_stagnated,
                            "fallback": True,
                            "fallback_stage": "retrieval",
                            "fallback_reason": runtime.abstain_reason,
                            "error_code": exc.code,
                            "route_selected": runtime.route_selected,
                            "route_retriever": runtime.route_retriever_name,
                            "route_provider": runtime.route_provider_name,
                        }

                elif state == AgentState.EVALUATE_EVIDENCE:
                    action = "evaluate_evidence"
                    candidates = runtime.candidates or []
                    runtime.assessment = self._evidence_judge.judge(
                        query=runtime.current_query,
                        candidates=candidates,
                    )
                    if not runtime.assessment.sufficient and runtime.retrieval_stagnated:
                        runtime.abstain_reason = "retrieval_stagnated"
                    if not runtime.assessment.sufficient and runtime.rewrite_count >= self._settings.agent_max_rewrites:
                        runtime.abstain_reason = runtime.assessment.reason

                    input_summary = f"evaluate candidates={len(candidates)}"
                    output_summary = (
                        f"sufficient={runtime.assessment.sufficient}, conflict={runtime.assessment.conflict}, "
                        f"reason={runtime.assessment.reason}, "
                        f"retrieval_stagnated={runtime.retrieval_stagnated}"
                    )
                    input_payload = {
                        "candidate_count": len(candidates),
                        "rewrite_count": runtime.rewrite_count,
                    }
                    output_payload = {
                        "sufficient": runtime.assessment.sufficient,
                        "conflict": runtime.assessment.conflict,
                        "conflict_type": runtime.assessment.conflict_type,
                        "conflict_chunk_ids": [
                            str(chunk_id) for chunk_id in runtime.assessment.conflict_chunk_ids
                        ],
                        "conflict_score_gap": runtime.assessment.conflict_score_gap,
                        "reason": runtime.assessment.reason,
                        "retrieval_stagnated": runtime.retrieval_stagnated,
                        "stagnation_count": runtime.retrieval_stagnation_count,
                        "last_top_score": runtime.last_retrieval_top_score,
                        "can_rewrite": runtime.rewrite_count < self._settings.agent_max_rewrites,
                    }

                elif state == AgentState.REWRITE_QUERY:
                    action = "rewrite_query"
                    if runtime.rewrite_count >= self._settings.agent_max_rewrites:
                        runtime.abstain_reason = "rewrite_limit_reached"
                        output_summary = runtime.abstain_reason
                        output_payload = {"fallback": True, "reason": runtime.abstain_reason}
                    else:
                        runtime.rewrite_count += 1
                        reason = runtime.assessment.reason if runtime.assessment else "insufficient_evidence"
                        rewritten = self._rewrite_strategy.rewrite(
                            query=runtime.current_query,
                            attempt=runtime.rewrite_count,
                            reason=reason,
                        )
                        input_summary = f"rewrite attempt={runtime.rewrite_count}"
                        output_summary = f"rewritten_query={rewritten[:80]}"
                        input_payload = {
                            "original_query": runtime.current_query[:160],
                            "reason": reason,
                            "stagnation_count": runtime.retrieval_stagnation_count,
                        }
                        output_payload = {"rewritten_query": rewritten[:200]}
                        runtime.current_query = rewritten

                elif state == AgentState.RERANK:
                    action = "rerank"
                    candidates = runtime.candidates or []
                    input_summary = f"candidates={len(candidates)}"
                    input_payload = {"candidate_count": len(candidates)}
                    try:
                        runtime.reranked = await call_with_resilience(
                            operation="rerank",
                            provider_name=type(self._reranker).__name__,
                            policy=rerank_policy,
                            call=lambda candidates=candidates, query=runtime.current_query: self._reranker.rerank(
                                query=query,
                                candidates=candidates,
                                top_n=min(
                                    self._settings.agent_rerank_top_n,
                                    max(len(candidates), 1),
                                ),
                                request_id=request_id,
                                trace_id=trace_id,
                            ),
                            logger=self._logger,
                            request_id=request_id,
                            trace_id=trace_id,
                            query_id=query_id,
                            agent_state=state.value,
                        )
                    except AppError as exc:
                        runtime.fallback_used = True
                        runtime.reranked = candidates
                        output_payload = {
                            "fallback": True,
                            "fallback_stage": "rerank",
                            "fallback_reason": "rerank_failure_fallback",
                            "error_code": exc.code,
                        }

                    reranked_before_filter = len(runtime.reranked or [])
                    filter_min_score = max(runtime.score_threshold, self._settings.agent_filter_min_score)
                    filtered = self._evidence_filter.filter(
                        query=runtime.current_query,
                        candidates=runtime.reranked or [],
                        min_score=filter_min_score,
                        top_n=self._settings.agent_rerank_top_n,
                    )
                    runtime.reranked = filtered
                    runtime.rerank_empty = len(filtered) == 0
                    if runtime.rerank_empty:
                        runtime.abstain_reason = "filtered_evidence_empty"

                    output_summary = (
                        f"reranked={reranked_before_filter} filtered={len(filtered)} "
                        f"empty={runtime.rerank_empty}"
                    )
                    output_payload = {
                        **output_payload,
                        "reranked_count_before_filter": reranked_before_filter,
                        "reranked_count": len(filtered),
                        "filter_min_score": filter_min_score,
                        "max_chunks_per_document": self._settings.agent_max_chunks_per_document,
                        "rerank_empty": runtime.rerank_empty,
                        "fallback": bool(output_payload.get("fallback", False)),
                    }

                elif state == AgentState.GENERATE_ANSWER:
                    action = "generate_answer"
                    ranked = runtime.reranked if runtime.reranked else (runtime.candidates or [])
                    citations = self._citation_assembler.assemble(ranked_chunks=ranked)
                    try:
                        answer = await call_with_resilience(
                            operation="generation",
                            provider_name=type(self._answer_generator).__name__,
                            policy=generation_policy,
                            call=lambda citations=citations, query=runtime.current_query: self._answer_generator.generate(
                                query=query,
                                citations=citations,
                                request_id=request_id,
                                trace_id=trace_id,
                            ),
                            logger=self._logger,
                            request_id=request_id,
                            trace_id=trace_id,
                            query_id=query_id,
                            agent_state=state.value,
                        )
                        if runtime.assessment and runtime.assessment.conflict and not answer.abstained:
                            answer = GeneratedAnswer(
                                text=(
                                    "Evidence appears to be partially conflicting; answer may be uncertain.\n"
                                    f"{answer.text}"
                                ),
                                citations=answer.citations,
                                abstained=False,
                                reason="evidence_conflict",
                            )
                        runtime.answer = answer
                        output_payload = {
                            "abstained": answer.abstained,
                            "reason": answer.reason,
                            "conflict": bool(runtime.assessment.conflict) if runtime.assessment else False,
                            "conflict_type": runtime.assessment.conflict_type if runtime.assessment else None,
                            "conflict_chunk_ids": [
                                str(chunk_id)
                                for chunk_id in (runtime.assessment.conflict_chunk_ids if runtime.assessment else [])
                            ],
                        }
                    except AppError as exc:
                        runtime.fallback_used = True
                        runtime.answer = GeneratedAnswer(
                            text="Insufficient evidence to answer reliably.",
                            citations=citations,
                            abstained=True,
                            reason="generation_failure_fallback",
                        )
                        output_payload = {
                            "abstained": True,
                            "reason": runtime.answer.reason,
                            "fallback": True,
                            "fallback_stage": "generation",
                            "fallback_reason": "generation_failure_fallback",
                            "error_code": exc.code,
                        }
                    input_summary = f"citations={len(citations)}"
                    output_summary = (
                        f"abstained={runtime.answer.abstained}, reason={runtime.answer.reason}"
                    )
                    input_payload = {"citation_count": len(citations)}

                elif state == AgentState.CRITIQUE:
                    action = "critique_answer"
                    input_summary = "critique generated answer and evidence support"
                    runtime.critique_failed = False
                    runtime.critique_requires_abstain = False

                    if runtime.answer is None:
                        runtime.critique_failed = True
                        runtime.failure_reason = "critique_answer_missing"
                        runtime.critique_reason = runtime.failure_reason
                        output_summary = runtime.failure_reason
                        input_payload = {"answer_present": False}
                        output_payload = {
                            "critique_failed": True,
                            "reason": runtime.failure_reason,
                            "fallback": True,
                        }
                    else:
                        citations_count = len(runtime.answer.citations)
                        conflict = bool(runtime.assessment.conflict) if runtime.assessment else False
                        fidelity_supported = runtime.answer.abstained or citations_count > 0
                        uncertainty_marked = (
                            "uncertain" in runtime.answer.text.lower()
                            or runtime.answer.reason == "evidence_conflict"
                        )

                        input_payload = {
                            "answer_abstained": runtime.answer.abstained,
                            "answer_reason": runtime.answer.reason,
                            "citation_count": citations_count,
                            "conflict": conflict,
                            "conflict_type": runtime.assessment.conflict_type if runtime.assessment else None,
                            "conflict_chunk_ids": [
                                str(chunk_id)
                                for chunk_id in (runtime.assessment.conflict_chunk_ids if runtime.assessment else [])
                            ],
                        }
                        runtime.critique_reason = "answer_supported_by_evidence"

                        if not runtime.answer.abstained and citations_count == 0:
                            runtime.fallback_used = True
                            runtime.critique_requires_abstain = True
                            runtime.critique_reason = "critique_missing_citations"
                            runtime.abstain_reason = runtime.critique_reason
                            runtime.answer = GeneratedAnswer(
                                text="Insufficient evidence to answer reliably.",
                                citations=[],
                                abstained=True,
                                reason=runtime.critique_reason,
                            )
                            fidelity_supported = False
                        elif runtime.answer.abstained:
                            runtime.critique_requires_abstain = True
                            runtime.abstain_reason = runtime.answer.reason or runtime.abstain_reason
                            runtime.critique_reason = runtime.answer.reason or "abstained"
                        elif conflict:
                            if not uncertainty_marked:
                                runtime.answer = GeneratedAnswer(
                                    text=(
                                        "Evidence appears to be partially conflicting; answer may be uncertain.\n"
                                        f"{runtime.answer.text}"
                                    ),
                                    citations=runtime.answer.citations,
                                    abstained=False,
                                    reason="evidence_conflict",
                                )
                                uncertainty_marked = True
                            runtime.critique_reason = "evidence_conflict_reviewed"

                        output_summary = (
                            f"critique_requires_abstain={runtime.critique_requires_abstain}, "
                            f"reason={runtime.critique_reason}"
                        )
                        output_payload = {
                            "critique_failed": runtime.critique_failed,
                            "critique_requires_abstain": runtime.critique_requires_abstain,
                            "fidelity_supported": fidelity_supported,
                            "conflict": conflict,
                            "conflict_type": runtime.assessment.conflict_type if runtime.assessment else None,
                            "conflict_chunk_ids": [
                                str(chunk_id)
                                for chunk_id in (runtime.assessment.conflict_chunk_ids if runtime.assessment else [])
                            ],
                            "uncertainty_marked": uncertainty_marked if conflict else False,
                            "reason": runtime.critique_reason,
                            "fallback": runtime.fallback_used,
                        }

                elif state == AgentState.ABSTAIN:
                    action = "abstain"
                    ranked = runtime.reranked if runtime.reranked else (runtime.candidates or [])
                    citations = self._citation_assembler.assemble(ranked_chunks=ranked)
                    reason = runtime.abstain_reason or "insufficient_evidence"
                    runtime.answer = GeneratedAnswer(
                        text="Insufficient evidence to answer reliably.",
                        citations=citations,
                        abstained=True,
                        reason=reason,
                    )
                    input_summary = "forced abstain"
                    output_summary = f"reason={reason}"
                    input_payload = {"candidate_count": len(ranked)}
                    output_payload = {"reason": reason, "fallback": True}

                elif state == AgentState.COMPLETE:
                    action = "complete"
                    input_summary = "finalize"
                    output_summary = "completed"
                    input_payload = {}
                    output_payload = {}

                else:
                    action = "failed"
                    reason = runtime.failure_reason or "unexpected_state"
                    runtime.answer = GeneratedAnswer(
                        text="System failed to complete reasoning; returning safe fallback.",
                        citations=[],
                        abstained=True,
                        reason=reason,
                    )
                    input_summary = "failed"
                    output_summary = reason
                    input_payload = {}
                    output_payload = {"reason": reason, "fallback": True}

                if state in TERMINAL_STATES:
                    next_state = state
                else:
                    next_value = self._policy.next_state(
                        current_state=state.value,
                        context={
                            "need_retrieval": runtime.need_retrieval,
                            "route_failed": runtime.route_failed,
                            "route_fallback_to_abstain": runtime.route_fallback_to_abstain,
                            "retrieval_fallback_to_abstain": runtime.retrieve_fallback_to_abstain,
                            "retrieval_failed": runtime.failure_reason == "retrieval_error",
                            "retrieval_stagnated": runtime.retrieval_stagnated,
                            "evidence_sufficient": runtime.assessment.sufficient if runtime.assessment else False,
                            "can_rewrite": runtime.rewrite_count < self._settings.agent_max_rewrites,
                            "rewrite_failed": runtime.failure_reason == "rewrite_error",
                            "rerank_empty": runtime.rerank_empty,
                            "rerank_failed": runtime.failure_reason == "rerank_error",
                            "generation_failed": runtime.failure_reason == "generation_error",
                            "critique_failed": runtime.critique_failed,
                            "critique_requires_abstain": runtime.critique_requires_abstain,
                        },
                    )
                    next_state = AgentState(next_value)

                    if not self._policy.validate_next_state(current_state=state, next_state=next_state):
                        raise ValueError(f"invalid_transition:{state.value}->{next_state.value}")

                latency_ms = int((time.perf_counter() - started) * 1000)
                steps.append(
                    self._record_step(
                        trace_id=trace_row.id,
                        request_id=request_id,
                        query_id=query_id,
                        step_order=step_order,
                        state=state,
                        action=action,
                        status=StepStatus.SUCCESS,
                        input_summary=input_summary,
                        output_summary=f"{output_summary}; next={next_state.value}",
                        input_payload=input_payload,
                        output_payload={"next_state": next_state.value, **output_payload},
                        latency_ms=latency_ms,
                    )
                )

                if state in TERMINAL_STATES:
                    break

                state = next_state

            except Exception as exc:
                latency_ms = int((time.perf_counter() - started) * 1000)
                runtime.failure_reason = str(exc)
                steps.append(
                    self._record_step(
                        trace_id=trace_row.id,
                        request_id=request_id,
                        query_id=query_id,
                        step_order=step_order,
                        state=state,
                        action=action or "execute",
                        status=StepStatus.FAILED,
                        input_summary=input_summary or "step_input",
                        output_summary="failed",
                        input_payload=input_payload,
                        output_payload={"fallback": True},
                        latency_ms=latency_ms,
                        error_message=str(exc),
                    )
                )
                state = AgentState.FAILED
                break

        if state == AgentState.FAILED and runtime.answer is None:
            runtime.answer = GeneratedAnswer(
                text="System failed to complete reasoning; returning safe fallback.",
                citations=[],
                abstained=True,
                reason=runtime.failure_reason or "agent_failed",
            )

        if state == AgentState.COMPLETE and runtime.answer is not None and runtime.answer.abstained:
            trace_status = TraceStatus.ABSTAINED
        elif state == AgentState.ABSTAIN:
            trace_status = TraceStatus.ABSTAINED
        elif state == AgentState.FAILED:
            trace_status = TraceStatus.FAILED
        else:
            trace_status = TraceStatus.SUCCESS

        trace_row.status = trace_status
        trace_row.end_state = state.value
        trace_row.finished_at = datetime.now(UTC)
        trace_row.meta = {
            **(trace_row.meta or {}),
            "rewrite_count": runtime.rewrite_count,
            "fallback_used": runtime.fallback_used,
            "abstain_reason": runtime.abstain_reason,
            "route_selected": runtime.route_selected,
            "route_retriever": runtime.route_retriever_name,
            "route_provider": runtime.route_provider_name,
            "route_reason": runtime.route_reason,
            "retrieval_stagnation_count": runtime.retrieval_stagnation_count,
            "conflict": bool(runtime.assessment.conflict) if runtime.assessment else False,
            "conflict_type": runtime.assessment.conflict_type if runtime.assessment else None,
            "conflict_chunk_ids": [
                str(chunk_id) for chunk_id in (runtime.assessment.conflict_chunk_ids if runtime.assessment else [])
            ],
            "critique_reason": runtime.critique_reason,
        }

        ranked = runtime.reranked if runtime.reranked else (runtime.candidates or [])
        citations = runtime.answer.citations if runtime.answer else []
        answer = runtime.answer or GeneratedAnswer(
            text="System failed to complete reasoning; returning safe fallback.",
            citations=[],
            abstained=True,
            reason="agent_failed",
        )

        return AgentExecutionResult(
            trace_db_id=trace_row.id,
            final_state=state,
            ranked_chunks=ranked,
            citations=citations,
            answer=answer,
            steps=steps,
        )
