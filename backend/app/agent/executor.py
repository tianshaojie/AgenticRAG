from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.agent.evidence import DefaultEvidenceSufficiencyJudge
from app.agent.interfaces import EvidenceSufficiencyJudge, QueryRewriteStrategy
from app.agent.models import AgentExecutionResult, AgentStepModel, EvidenceAssessment
from app.agent.policy import DefaultAgentPolicy
from app.agent.rewrite import DefaultQueryRewriteStrategy
from app.agent.state_machine import AgentState, TERMINAL_STATES
from app.core.config import Settings
from app.core.errors import AppError
from app.core.resilience import ResiliencePolicy, call_with_resilience
from app.db.models import AgentTrace, AgentTraceStep
from app.domain.enums import StepStatus, TraceStatus
from app.domain.interfaces import (
    AnswerGenerator,
    CitationAssembler,
    GeneratedAnswer,
    Retriever,
    Reranker,
    ScoredChunk,
)


@dataclass(slots=True)
class _RuntimeContext:
    original_query: str
    current_query: str
    top_k: int
    score_threshold: float
    embedding_model: str
    rewrite_count: int = 0
    need_retrieval: bool = True
    candidates: list[ScoredChunk] | None = None
    reranked: list[ScoredChunk] | None = None
    assessment: EvidenceAssessment | None = None
    answer: GeneratedAnswer | None = None
    fallback_used: bool = False
    failure_reason: str | None = None
    abstain_reason: str | None = None
    retrieve_fallback_to_abstain: bool = False


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
        rewrite_strategy: QueryRewriteStrategy | None = None,
        evidence_judge: EvidenceSufficiencyJudge | None = None,
    ) -> None:
        self._db = db
        self._settings = settings
        self._retriever = retriever
        self._reranker = reranker
        self._citation_assembler = citation_assembler
        self._answer_generator = answer_generator
        self._policy = policy or DefaultAgentPolicy()
        self._rewrite_strategy = rewrite_strategy or DefaultQueryRewriteStrategy()
        self._logger = logging.getLogger("app.agent")
        self._evidence_judge = evidence_judge or DefaultEvidenceSufficiencyJudge(
            min_results=settings.agent_min_evidence_results,
            min_score=settings.evidence_min_score,
            conflict_delta=settings.agent_conflict_score_delta,
        )

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
                    cleaned = runtime.current_query.strip()
                    runtime.need_retrieval = len(cleaned) >= self._settings.agent_query_min_chars
                    if not runtime.need_retrieval:
                        runtime.abstain_reason = "query_too_short"
                    input_summary = "analyze query for retrieval need"
                    output_summary = (
                        "retrieval_required" if runtime.need_retrieval else "skip_retrieval_abstain"
                    )
                    input_payload = {"query": cleaned[:200]}
                    output_payload = {"need_retrieval": runtime.need_retrieval}

                elif state == AgentState.RETRIEVE:
                    action = "retrieve"
                    input_summary = f"query={runtime.current_query[:120]}"
                    input_payload = {
                        "query": runtime.current_query[:200],
                        "top_k": runtime.top_k,
                        "score_threshold": runtime.score_threshold,
                    }
                    runtime.retrieve_fallback_to_abstain = False
                    try:
                        runtime.candidates = await call_with_resilience(
                            operation="retrieval",
                            provider_name=type(self._retriever).__name__,
                            policy=retrieval_policy,
                            call=lambda: self._retriever.retrieve(
                                query=runtime.current_query,
                                top_k=runtime.top_k,
                                score_threshold=runtime.score_threshold,
                                model=runtime.embedding_model,
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
                        output_summary = f"retrieved={len(runtime.candidates)} top_score={top_score:.3f}"
                        output_payload = {
                            "retrieved_count": len(runtime.candidates),
                            "top_score": top_score,
                            "fallback": fallback_used,
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
                            "fallback": True,
                            "fallback_stage": "retrieval",
                            "fallback_reason": runtime.abstain_reason,
                            "error_code": exc.code,
                        }

                elif state == AgentState.EVALUATE_EVIDENCE:
                    action = "evaluate_evidence"
                    candidates = runtime.candidates or []
                    runtime.assessment = self._evidence_judge.judge(
                        query=runtime.current_query,
                        candidates=candidates,
                    )
                    if not runtime.assessment.sufficient and runtime.rewrite_count >= self._settings.agent_max_rewrites:
                        runtime.abstain_reason = runtime.assessment.reason

                    input_summary = f"evaluate candidates={len(candidates)}"
                    output_summary = (
                        f"sufficient={runtime.assessment.sufficient}, conflict={runtime.assessment.conflict}, "
                        f"reason={runtime.assessment.reason}"
                    )
                    input_payload = {
                        "candidate_count": len(candidates),
                        "rewrite_count": runtime.rewrite_count,
                    }
                    output_payload = {
                        "sufficient": runtime.assessment.sufficient,
                        "conflict": runtime.assessment.conflict,
                        "reason": runtime.assessment.reason,
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
                        input_payload = {"original_query": runtime.current_query[:160], "reason": reason}
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
                            call=lambda: self._reranker.rerank(
                                query=runtime.current_query,
                                candidates=candidates,
                                top_n=min(self._settings.agent_rerank_top_n, max(len(candidates), 1)),
                                request_id=request_id,
                                trace_id=trace_id,
                            ),
                            logger=self._logger,
                            request_id=request_id,
                            trace_id=trace_id,
                            query_id=query_id,
                            agent_state=state.value,
                        )
                        output_summary = f"reranked={len(runtime.reranked)}"
                        output_payload = {
                            "reranked_count": len(runtime.reranked),
                            "fallback": runtime.fallback_used,
                        }
                    except AppError as exc:
                        runtime.fallback_used = True
                        runtime.reranked = candidates
                        output_summary = "rerank_failed_fallback_to_candidates"
                        output_payload = {
                            "reranked_count": len(runtime.reranked),
                            "fallback": True,
                            "fallback_stage": "rerank",
                            "fallback_reason": "rerank_failure_fallback",
                            "error_code": exc.code,
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
                            call=lambda: self._answer_generator.generate(
                                query=runtime.current_query,
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
                        output_payload = {"abstained": answer.abstained, "reason": answer.reason}
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
                            "retrieval_fallback_to_abstain": runtime.retrieve_fallback_to_abstain,
                            "retrieval_failed": runtime.failure_reason == "retrieval_error",
                            "evidence_sufficient": runtime.assessment.sufficient if runtime.assessment else False,
                            "can_rewrite": runtime.rewrite_count < self._settings.agent_max_rewrites,
                            "rewrite_failed": runtime.failure_reason == "rewrite_error",
                            "rerank_failed": runtime.failure_reason == "rerank_error",
                            "generation_failed": runtime.failure_reason == "generation_error",
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
