from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(slots=True)
class AgentExecutionResult:
    trace_db_id: UUID
    final_state: AgentState
    ranked_chunks: list[ScoredChunk]
    citations: list[CitationRecord]
    answer: GeneratedAnswer
    steps: list[AgentStepModel]
