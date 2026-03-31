import pytest

from app.agent.policy import DefaultAgentPolicy
from app.agent.state_machine import AgentState, validate_transition


@pytest.mark.parametrize(
    ("current", "context", "expected"),
    [
        (AgentState.INIT, {}, AgentState.ANALYZE_QUERY),
        (AgentState.ANALYZE_QUERY, {"need_retrieval": True}, AgentState.RETRIEVE),
        (AgentState.ANALYZE_QUERY, {"need_retrieval": False}, AgentState.ABSTAIN),
        (AgentState.RETRIEVE, {"retrieval_failed": False}, AgentState.EVALUATE_EVIDENCE),
        (AgentState.EVALUATE_EVIDENCE, {"evidence_sufficient": True}, AgentState.RERANK),
        (
            AgentState.EVALUATE_EVIDENCE,
            {"evidence_sufficient": False, "can_rewrite": True},
            AgentState.REWRITE_QUERY,
        ),
        (
            AgentState.EVALUATE_EVIDENCE,
            {"evidence_sufficient": False, "can_rewrite": False},
            AgentState.ABSTAIN,
        ),
        (AgentState.REWRITE_QUERY, {"rewrite_failed": False}, AgentState.RETRIEVE),
        (AgentState.RERANK, {"rerank_failed": False}, AgentState.GENERATE_ANSWER),
        (AgentState.GENERATE_ANSWER, {"generation_failed": False}, AgentState.COMPLETE),
    ],
)
def test_default_policy_transitions(current: AgentState, context: dict, expected: AgentState) -> None:
    policy = DefaultAgentPolicy()
    next_state = AgentState(policy.next_state(current_state=current.value, context=context))
    assert next_state == expected
    assert validate_transition(current, next_state)


def test_terminal_state_returns_itself() -> None:
    policy = DefaultAgentPolicy()

    assert policy.next_state(current_state=AgentState.ABSTAIN.value, context={}) == AgentState.ABSTAIN.value
    assert policy.next_state(current_state=AgentState.COMPLETE.value, context={}) == AgentState.COMPLETE.value
    assert policy.next_state(current_state=AgentState.FAILED.value, context={}) == AgentState.FAILED.value
