from __future__ import annotations

from enum import Enum


class AgentState(str, Enum):
    RECEIVED = "RECEIVED"
    RETRIEVING = "RETRIEVING"
    RERANKING = "RERANKING"
    SYNTHESIZING = "SYNTHESIZING"
    CITING = "CITING"
    COMPLETE = "COMPLETE"
    ABSTAIN = "ABSTAIN"
    FAILED = "FAILED"


ALLOWED_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.RECEIVED: {AgentState.RETRIEVING, AgentState.FAILED},
    AgentState.RETRIEVING: {AgentState.RERANKING, AgentState.ABSTAIN, AgentState.FAILED},
    AgentState.RERANKING: {AgentState.SYNTHESIZING, AgentState.ABSTAIN, AgentState.FAILED},
    AgentState.SYNTHESIZING: {AgentState.CITING, AgentState.ABSTAIN, AgentState.FAILED},
    AgentState.CITING: {AgentState.COMPLETE, AgentState.ABSTAIN, AgentState.FAILED},
    AgentState.COMPLETE: set(),
    AgentState.ABSTAIN: set(),
    AgentState.FAILED: set(),
}


def validate_transition(current: AgentState, nxt: AgentState) -> bool:
    return nxt in ALLOWED_TRANSITIONS[current]
