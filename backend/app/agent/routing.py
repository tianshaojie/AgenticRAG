from __future__ import annotations

from app.agent.interfaces import QueryRouter
from app.agent.models import QueryAnalysis, RouteDecision


def _normalize_routes(routes: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for route in routes:
        key = route.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


class HeuristicQueryRouter(QueryRouter):
    """Conservative deterministic router with explicit fallback path."""

    _INTENT_ROUTE_MAP: dict[str, str] = {
        "knowledge_lookup": "pgvector",
        "structured_query": "sql",
        "external_lookup": "api",
    }

    def route(self, *, analysis: QueryAnalysis, available_routes: list[str]) -> RouteDecision:
        routes = _normalize_routes(available_routes)
        if not analysis.need_retrieval:
            return RouteDecision(
                preferred_route="none",
                selected_route="abstain",
                available_routes=routes,
                reason="query_analysis_skip_retrieval",
                fallback=False,
                confidence=analysis.confidence,
            )

        preferred_route = self._INTENT_ROUTE_MAP.get(analysis.intent, "pgvector")
        fallback = False
        if preferred_route in routes:
            selected_route = preferred_route
            reason = "preferred_route_available"
        elif "pgvector" in routes:
            selected_route = "pgvector"
            fallback = True
            reason = f"{preferred_route}_route_unavailable_fallback_pgvector"
        elif routes:
            selected_route = routes[0]
            fallback = True
            reason = f"{preferred_route}_route_unavailable_fallback_first_available"
        else:
            selected_route = "abstain"
            fallback = True
            reason = "no_available_routes"

        confidence = analysis.confidence - (0.15 if fallback else 0.0)
        confidence = max(0.0, min(1.0, confidence))

        return RouteDecision(
            preferred_route=preferred_route,
            selected_route=selected_route,
            available_routes=routes,
            reason=reason,
            fallback=fallback,
            confidence=confidence,
        )
