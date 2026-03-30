from app.agent.state_machine import ALLOWED_TRANSITIONS, AgentState, validate_transition


def test_terminal_states_have_no_outgoing_edges() -> None:
    assert ALLOWED_TRANSITIONS[AgentState.COMPLETE] == set()
    assert ALLOWED_TRANSITIONS[AgentState.ABSTAIN] == set()
    assert ALLOWED_TRANSITIONS[AgentState.FAILED] == set()


def test_validate_transition_rejects_invalid_path() -> None:
    assert validate_transition(AgentState.RECEIVED, AgentState.RETRIEVING) is True
    assert validate_transition(AgentState.RECEIVED, AgentState.COMPLETE) is False
