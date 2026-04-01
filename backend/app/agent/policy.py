from __future__ import annotations

from app.agent.state_machine import AgentState, validate_transition
from app.domain.interfaces import AgentPolicy


class DefaultAgentPolicy(AgentPolicy):
    def next_state(self, *, current_state: str, context: dict[str, object]) -> str:
        state = AgentState(current_state)

        if state == AgentState.INIT:
            return AgentState.ANALYZE_QUERY.value

        if state == AgentState.ANALYZE_QUERY:
            if bool(context.get("need_retrieval", True)):
                return AgentState.ROUTE.value
            return AgentState.ABSTAIN.value

        if state == AgentState.ROUTE:
            if bool(context.get("route_fallback_to_abstain", False)):
                return AgentState.ABSTAIN.value
            if bool(context.get("route_failed", False)):
                return AgentState.FAILED.value
            return AgentState.RETRIEVE.value

        if state == AgentState.RETRIEVE:
            if bool(context.get("retrieval_fallback_to_abstain", False)):
                return AgentState.ABSTAIN.value
            if bool(context.get("retrieval_failed", False)):
                return AgentState.FAILED.value
            return AgentState.EVALUATE_EVIDENCE.value

        if state == AgentState.EVALUATE_EVIDENCE:
            if bool(context.get("retrieval_stagnated", False)) and not bool(
                context.get("evidence_sufficient", False)
            ):
                return AgentState.ABSTAIN.value
            if bool(context.get("evidence_sufficient", False)):
                return AgentState.RERANK.value
            if bool(context.get("can_rewrite", False)):
                return AgentState.REWRITE_QUERY.value
            return AgentState.ABSTAIN.value

        if state == AgentState.REWRITE_QUERY:
            if bool(context.get("rewrite_failed", False)):
                return AgentState.FAILED.value
            return AgentState.RETRIEVE.value

        if state == AgentState.RERANK:
            if bool(context.get("rerank_empty", False)):
                return AgentState.ABSTAIN.value
            if bool(context.get("rerank_failed", False)):
                return AgentState.FAILED.value
            return AgentState.GENERATE_ANSWER.value

        if state == AgentState.GENERATE_ANSWER:
            if bool(context.get("generation_failed", False)):
                return AgentState.FAILED.value
            return AgentState.CRITIQUE.value

        if state == AgentState.CRITIQUE:
            if bool(context.get("critique_failed", False)):
                return AgentState.FAILED.value
            if bool(context.get("critique_requires_abstain", False)):
                return AgentState.ABSTAIN.value
            return AgentState.COMPLETE.value

        if state in {AgentState.ABSTAIN, AgentState.COMPLETE, AgentState.FAILED}:
            return state.value

        return AgentState.FAILED.value

    def validate_next_state(self, *, current_state: AgentState, next_state: AgentState) -> bool:
        return validate_transition(current_state, next_state)
