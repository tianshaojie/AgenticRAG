from __future__ import annotations

from app.agent.models import QueryAnalysis
from app.agent.routing import HeuristicQueryRouter


def _analysis(*, intent: str, need_retrieval: bool = True) -> QueryAnalysis:
    return QueryAnalysis(
        original_query="test",
        normalized_query="test",
        corrected_query="test",
        expanded_terms=[],
        intent=intent,
        need_retrieval=need_retrieval,
        confidence=0.9,
        reasons=["test"],
    )


def test_router_prefers_pgvector_for_knowledge_lookup() -> None:
    router = HeuristicQueryRouter()

    decision = router.route(analysis=_analysis(intent="knowledge_lookup"), available_routes=["pgvector"])

    assert decision.selected_route == "pgvector"
    assert decision.preferred_route == "pgvector"
    assert decision.fallback is False


def test_router_falls_back_to_pgvector_when_sql_is_unavailable() -> None:
    router = HeuristicQueryRouter()

    decision = router.route(analysis=_analysis(intent="structured_query"), available_routes=["pgvector"])

    assert decision.preferred_route == "sql"
    assert decision.selected_route == "pgvector"
    assert decision.fallback is True
    assert decision.reason == "sql_route_unavailable_fallback_pgvector"


def test_router_returns_abstain_when_no_routes_available() -> None:
    router = HeuristicQueryRouter()

    decision = router.route(analysis=_analysis(intent="knowledge_lookup"), available_routes=[])

    assert decision.selected_route == "abstain"
    assert decision.fallback is True
    assert decision.reason == "no_available_routes"


def test_router_skips_retrieval_when_analysis_disables_it() -> None:
    router = HeuristicQueryRouter()

    decision = router.route(
        analysis=_analysis(intent="chitchat", need_retrieval=False),
        available_routes=["pgvector", "api"],
    )

    assert decision.selected_route == "abstain"
    assert decision.fallback is False
    assert decision.reason == "query_analysis_skip_retrieval"
