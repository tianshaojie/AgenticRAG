from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings
from app.core.errors import ValidationAppError
from app.retrieval.route_provider_factory import (
    build_api_route_provider,
    build_route_retrievers,
    build_sql_route_provider,
)
from app.retrieval.route_providers import (
    ApiLexicalRouteProvider,
    ApiMockRouteProvider,
    SqlLexicalRouteProvider,
    SqlMockRouteProvider,
)
from app.retrieval.route_retrievers import ApiRouteRetriever, SqlRouteRetriever


class _DummyPgvectorRetriever:
    async def retrieve(self, *, query: str, top_k: int, score_threshold: float, model: str):
        _ = (query, top_k, score_threshold, model)
        return []


def test_settings_load_route_provider_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_AGENT_SQL_ROUTE_PROVIDER", "mock")
    monkeypatch.setenv("RAG_AGENT_API_ROUTE_PROVIDER", "lexical")
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.agent_sql_route_provider == "mock"
    assert settings.agent_api_route_provider == "lexical"

    monkeypatch.delenv("RAG_AGENT_SQL_ROUTE_PROVIDER", raising=False)
    monkeypatch.delenv("RAG_AGENT_API_ROUTE_PROVIDER", raising=False)
    get_settings.cache_clear()


@pytest.mark.integration
def test_route_provider_factory_builds_configured_providers(db_session) -> None:
    settings = Settings(agent_sql_route_provider="mock", agent_api_route_provider="lexical")

    sql_provider = build_sql_route_provider(settings=settings, db=db_session)
    api_provider = build_api_route_provider(settings=settings, db=db_session)

    assert isinstance(sql_provider, SqlMockRouteProvider)
    assert isinstance(api_provider, ApiLexicalRouteProvider)


@pytest.mark.integration
def test_route_provider_factory_rejects_unsupported_provider(db_session) -> None:
    settings = Settings(agent_sql_route_provider="lexical")
    settings.agent_api_route_provider = "invalid"  # type: ignore[assignment]

    with pytest.raises(ValidationAppError) as exc_info:
        _ = build_api_route_provider(settings=settings, db=db_session)

    assert exc_info.value.code == "agent_api_route_provider_not_supported"


@pytest.mark.integration
def test_route_retriever_factory_builds_provider_backed_retrievers(db_session) -> None:
    settings = Settings(agent_sql_route_provider="lexical", agent_api_route_provider="mock")

    retrievers = build_route_retrievers(
        settings=settings,
        db=db_session,
        pgvector_retriever=_DummyPgvectorRetriever(),
    )

    assert set(retrievers.keys()) == {"pgvector", "sql", "api"}
    assert isinstance(retrievers["sql"], SqlRouteRetriever)
    assert isinstance(retrievers["api"], ApiRouteRetriever)
    assert retrievers["sql"].provider_name == "sql_lexical"
    assert retrievers["api"].provider_name == "api_mock"


@pytest.mark.integration
def test_route_provider_factory_builds_lexical_variants(db_session) -> None:
    settings = Settings(agent_sql_route_provider="lexical", agent_api_route_provider="mock")

    sql_provider = build_sql_route_provider(settings=settings, db=db_session)
    api_provider = build_api_route_provider(settings=settings, db=db_session)

    assert isinstance(sql_provider, SqlLexicalRouteProvider)
    assert isinstance(api_provider, ApiMockRouteProvider)
