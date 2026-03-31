from __future__ import annotations

from enum import Enum


class AgentState(str, Enum):
    INIT = "INIT"
    ANALYZE_QUERY = "ANALYZE_QUERY"
    RETRIEVE = "RETRIEVE"
    EVALUATE_EVIDENCE = "EVALUATE_EVIDENCE"
    REWRITE_QUERY = "REWRITE_QUERY"
    RERANK = "RERANK"
    GENERATE_ANSWER = "GENERATE_ANSWER"
    ABSTAIN = "ABSTAIN"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


TERMINAL_STATES: set[AgentState] = {
    AgentState.ABSTAIN,
    AgentState.COMPLETE,
    AgentState.FAILED,
}


ALLOWED_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.INIT: {AgentState.ANALYZE_QUERY, AgentState.FAILED},
    AgentState.ANALYZE_QUERY: {AgentState.RETRIEVE, AgentState.ABSTAIN, AgentState.FAILED},
    AgentState.RETRIEVE: {AgentState.EVALUATE_EVIDENCE, AgentState.ABSTAIN, AgentState.FAILED},
    AgentState.EVALUATE_EVIDENCE: {
        AgentState.REWRITE_QUERY,
        AgentState.RERANK,
        AgentState.ABSTAIN,
        AgentState.FAILED,
    },
    AgentState.REWRITE_QUERY: {AgentState.RETRIEVE, AgentState.ABSTAIN, AgentState.FAILED},
    AgentState.RERANK: {AgentState.GENERATE_ANSWER, AgentState.FAILED},
    AgentState.GENERATE_ANSWER: {AgentState.COMPLETE, AgentState.FAILED},
    AgentState.ABSTAIN: set(),
    AgentState.COMPLETE: set(),
    AgentState.FAILED: set(),
}


def validate_transition(current: AgentState, nxt: AgentState) -> bool:
    return nxt in ALLOWED_TRANSITIONS[current]
