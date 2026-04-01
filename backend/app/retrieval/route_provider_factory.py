from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ValidationAppError
from app.domain.interfaces import Retriever
from app.retrieval.route_providers import (
    ApiLexicalRouteProvider,
    ApiMockRouteProvider,
    RouteRetrieverProvider,
    SqlLexicalRouteProvider,
    SqlMockRouteProvider,
)
from app.retrieval.route_retrievers import ApiRouteRetriever, SqlRouteRetriever


def build_sql_route_provider(*, settings: Settings, db: Session) -> RouteRetrieverProvider:
    logger = logging.getLogger("app.route_provider")
    provider_name = settings.agent_sql_route_provider
    if provider_name == "lexical":
        logger.info(
            "route_provider_selected",
            extra={
                "request_id": "startup",
                "trace_id": "startup",
                "provider_name": "sql_lexical",
                "operation": "route_provider_factory",
                "fallback_used": False,
            },
        )
        return SqlLexicalRouteProvider(db=db)
    if provider_name == "mock":
        logger.info(
            "route_provider_selected",
            extra={
                "request_id": "startup",
                "trace_id": "startup",
                "provider_name": "sql_mock",
                "operation": "route_provider_factory",
                "fallback_used": True,
            },
        )
        return SqlMockRouteProvider(db=db)
    raise ValidationAppError(
        code="agent_sql_route_provider_not_supported",
        message="configured sql route provider is not supported",
        details={"provider": provider_name},
    )


def build_api_route_provider(*, settings: Settings, db: Session) -> RouteRetrieverProvider:
    logger = logging.getLogger("app.route_provider")
    provider_name = settings.agent_api_route_provider
    if provider_name == "lexical":
        logger.info(
            "route_provider_selected",
            extra={
                "request_id": "startup",
                "trace_id": "startup",
                "provider_name": "api_lexical",
                "operation": "route_provider_factory",
                "fallback_used": False,
            },
        )
        return ApiLexicalRouteProvider(db=db)
    if provider_name == "mock":
        logger.info(
            "route_provider_selected",
            extra={
                "request_id": "startup",
                "trace_id": "startup",
                "provider_name": "api_mock",
                "operation": "route_provider_factory",
                "fallback_used": True,
            },
        )
        return ApiMockRouteProvider(db=db)
    raise ValidationAppError(
        code="agent_api_route_provider_not_supported",
        message="configured api route provider is not supported",
        details={"provider": provider_name},
    )


def build_route_retrievers(
    *,
    settings: Settings,
    db: Session,
    pgvector_retriever: Retriever,
) -> dict[str, Retriever]:
    return {
        "pgvector": pgvector_retriever,
        "sql": SqlRouteRetriever(provider=build_sql_route_provider(settings=settings, db=db)),
        "api": ApiRouteRetriever(provider=build_api_route_provider(settings=settings, db=db)),
    }
