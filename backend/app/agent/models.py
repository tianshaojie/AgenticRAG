from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.agent.state_machine import AgentState
from app.domain.interfaces import CitationRecord, GeneratedAnswer, ScoredChunk


@dataclass(slots=True)
class AgentStepModel:
    step_order: int
    state: AgentState
    action: str
    status: str
    input_summary: str
    output_summary: str
    latency_ms: int
    fallback: bool
    error_message: str | None = None


@dataclass(slots=True)
class AgentTraceModel:
    trace_db_id: UUID
    session_id: UUID
    state: AgentState
    status: str
    steps: list[AgentStepModel]


@dataclass(slots=True)
class EvidenceAssessment:
    sufficient: bool
    reason: str
    conflict: bool
    needs_rewrite: bool
    conflict_type: str | None = None
    conflict_chunk_ids: list[UUID] = field(default_factory=list)
    conflict_score_gap: float | None = None


@dataclass(slots=True)
class QueryAnalysis:
    original_query: str
    normalized_query: str
    corrected_query: str
    expanded_terms: list[str]
    intent: str
    need_retrieval: bool
    confidence: float
    reasons: list[str]


@dataclass(slots=True)
class RouteDecision:
    preferred_route: str
    selected_route: str
    available_routes: list[str]
    reason: str
    fallback: bool
    confidence: float


@dataclass(slots=True)
class AgentExecutionResult:
    trace_db_id: UUID
    final_state: AgentState
    ranked_chunks: list[ScoredChunk]
    citations: list[CitationRecord]
    answer: GeneratedAnswer
    steps: list[AgentStepModel]
