from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_metadata
from app.agent.executor import FiniteStateAgentExecutor
from app.agent.policy import DefaultAgentPolicy
from app.agent.rewrite import DefaultQueryRewriteStrategy
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.models import AgentTrace, EvalRun
from app.domain.enums import EvalRunStatus
from app.evals.runner import PgEvaluationRunner
from app.ingestion.service import SimpleDocumentIngestionService, UnsupportedDocumentError
from app.indexing.chunker import SlidingWindowChunker
from app.indexing.embedder import DeterministicEmbedder
from app.indexing.pgvector_index import PgVectorIndex
from app.indexing.service import DocumentIndexingService
from app.llm.factory import build_llm_provider
from app.llm.interfaces import LLMCompletionRequest, LLMMessage
from app.reranker.factory import build_reranker_provider
from app.reranker.interfaces import RerankRequest, RerankerCandidate
from app.retrieval.repository import RetrievalRepository
from app.retrieval.reranker_factory import build_reranker
from app.retrieval.service import PgVectorRetriever
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from app.schemas.common import Citation, CitationSpan, HealthCheck, HealthResponse, ReadyResponse, RequestMetadata
from app.schemas.documents import DocumentIndexRequest, DocumentIndexResponse, DocumentListResponse, DocumentRead
from app.schemas.evals import EvalResultRead, EvalRunRequest, EvalRunResponse, FailedEvalCase
from app.schemas.retrieval import RetrievalResult
from app.schemas.settings import (
    ProviderCheckItem,
    ProviderCheckRequest,
    ProviderCheckResponse,
    ProviderSettingsResponse,
    ProviderSettingsUpdateRequest,
    ProviderTarget,
    ProviderRuntimeConfig,
)
from app.schemas.traces import TraceRead, TraceStepRead
from app.observability.metrics import metrics
from app.services.answer_factory import build_answer_generator
from app.services.citation import BasicCitationAssembler
from app.services.rag_chat import RAGChatService

router = APIRouter()
logger = logging.getLogger("app.api")


def _mask_secret_last4(secret_value: str | None) -> str | None:
    if not secret_value:
        return None
    trimmed = secret_value.strip()
    if not trimmed:
        return None
    if len(trimmed) <= 4:
        return "*" * len(trimmed)
    return f"{'*' * max(len(trimmed) - 4, 4)}{trimmed[-4:]}"


def _llm_runtime_config(settings: Settings) -> ProviderRuntimeConfig:
    llm_api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    return ProviderRuntimeConfig(
        name="llm",
        provider=settings.llm_provider,
        enabled=settings.enable_real_llm_provider,
        has_api_key=bool(llm_api_key and llm_api_key.strip()),
        api_key_last4=_mask_secret_last4(llm_api_key),
        endpoint=settings.llm_endpoint,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


def _reranker_runtime_config(settings: Settings) -> ProviderRuntimeConfig:
    reranker_api_key = settings.reranker_api_key.get_secret_value() if settings.reranker_api_key else None
    return ProviderRuntimeConfig(
        name="reranker",
        provider=settings.reranker_provider,
        enabled=settings.enable_real_reranker_provider,
        has_api_key=bool(reranker_api_key and reranker_api_key.strip()),
        api_key_last4=_mask_secret_last4(reranker_api_key),
        endpoint=settings.reranker_endpoint,
        base_url=settings.reranker_base_url,
        model=settings.reranker_model,
        timeout_seconds=settings.reranker_timeout_seconds,
        max_retries=settings.reranker_max_retries,
    )


def _provider_settings_response(settings: Settings) -> ProviderSettingsResponse:
    return ProviderSettingsResponse(
        llm=_llm_runtime_config(settings),
        reranker=_reranker_runtime_config(settings),
    )


def _apply_runtime_provider_settings(settings: Settings, payload: ProviderSettingsUpdateRequest) -> None:
    if payload.llm_api_key is not None:
        clean = payload.llm_api_key.strip()
        settings.llm_api_key = SecretStr(clean) if clean else None
    if payload.reranker_api_key is not None:
        clean = payload.reranker_api_key.strip()
        settings.reranker_api_key = SecretStr(clean) if clean else None
    if payload.llm_endpoint is not None:
        settings.llm_endpoint = payload.llm_endpoint.strip()
    if payload.llm_base_url is not None:
        settings.llm_base_url = payload.llm_base_url.strip() or None
    if payload.llm_model is not None:
        settings.llm_model = payload.llm_model.strip()
    if payload.reranker_endpoint is not None:
        settings.reranker_endpoint = payload.reranker_endpoint.strip() or None
    if payload.reranker_base_url is not None:
        settings.reranker_base_url = payload.reranker_base_url.strip() or None
    if payload.reranker_model is not None:
        settings.reranker_model = payload.reranker_model.strip()
    if payload.enable_real_llm_provider is not None:
        settings.enable_real_llm_provider = payload.enable_real_llm_provider
    if payload.enable_real_reranker_provider is not None:
        settings.enable_real_reranker_provider = payload.enable_real_reranker_provider


def _derive_provider_check_status(checks: list[ProviderCheckItem]) -> str:
    if not checks:
        return "degraded"
    if all(check.status == "ok" for check in checks):
        return "ok"
    if any(check.status == "failed" for check in checks):
        return "failed"
    return "degraded"


def _format_app_error_detail(exc: AppError) -> str:
    detail = f"{exc.message} ({exc.code})"
    status_code = exc.details.get("status_code")
    if isinstance(status_code, int):
        return f"{detail} [status_code={status_code}]"
    return detail


async def _run_llm_provider_check(*, settings: Settings, request_metadata: RequestMetadata) -> ProviderCheckItem:
    checked_at = datetime.now(UTC)
    if not settings.enable_real_llm_provider:
        return ProviderCheckItem(
            provider="llm",
            status="degraded",
            detail="real llm provider is disabled",
            checked_at=checked_at,
            used_real_provider=False,
        )

    started = time.perf_counter()
    try:
        provider = build_llm_provider(settings=settings)
        completion = await provider.chat_completion(
            request=LLMCompletionRequest(
                messages=[
                    LLMMessage(role="system", content="health check"),
                    LLMMessage(role="user", content="Reply with OK"),
                ],
                model=settings.llm_model,
                temperature=0.0,
                max_tokens=8,
                timeout_seconds=float(settings.llm_timeout_seconds),
                request_id=request_metadata.request_id,
                trace_id=request_metadata.trace_id,
            )
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        model_name = completion.model or settings.llm_model
        return ProviderCheckItem(
            provider="llm",
            status="ok",
            detail=f"llm provider reachable (model={model_name})",
            checked_at=checked_at,
            latency_ms=latency_ms,
            used_real_provider=True,
        )
    except AppError as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return ProviderCheckItem(
            provider="llm",
            status="failed",
            detail=_format_app_error_detail(exc),
            checked_at=checked_at,
            latency_ms=latency_ms,
            used_real_provider=True,
        )
    except Exception:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return ProviderCheckItem(
            provider="llm",
            status="failed",
            detail="llm provider check failed unexpectedly",
            checked_at=checked_at,
            latency_ms=latency_ms,
            used_real_provider=True,
        )


async def _run_reranker_provider_check(
    *,
    settings: Settings,
    request_metadata: RequestMetadata,
) -> ProviderCheckItem:
    checked_at = datetime.now(UTC)
    if not settings.enable_reranking:
        return ProviderCheckItem(
            provider="reranker",
            status="degraded",
            detail="reranking is disabled",
            checked_at=checked_at,
            used_real_provider=False,
            fallback_used=True,
        )

    if not settings.enable_real_reranker_provider:
        return ProviderCheckItem(
            provider="reranker",
            status="degraded",
            detail="real reranker provider is disabled",
            checked_at=checked_at,
            used_real_provider=False,
            fallback_used=True,
        )

    started = time.perf_counter()
    try:
        provider = build_reranker_provider(settings=settings)
        response = await provider.rerank(
            request=RerankRequest(
                query="health check",
                candidates=[
                    RerankerCandidate(candidate_id="a", document="health check candidate"),
                    RerankerCandidate(candidate_id="b", document="fallback candidate"),
                ],
                top_n=1,
                model=settings.reranker_model,
                timeout_seconds=float(settings.reranker_timeout_seconds),
                request_id=request_metadata.request_id,
                trace_id=request_metadata.trace_id,
            )
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        model_name = response.model or settings.reranker_model
        return ProviderCheckItem(
            provider="reranker",
            status="ok",
            detail=f"reranker provider reachable (model={model_name})",
            checked_at=checked_at,
            latency_ms=latency_ms,
            used_real_provider=True,
        )
    except AppError as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return ProviderCheckItem(
            provider="reranker",
            status="failed",
            detail=_format_app_error_detail(exc),
            checked_at=checked_at,
            latency_ms=latency_ms,
            used_real_provider=True,
            fallback_used=True,
        )
    except Exception:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return ProviderCheckItem(
            provider="reranker",
            status="failed",
            detail="reranker provider check failed unexpectedly",
            checked_at=checked_at,
            latency_ms=latency_ms,
            used_real_provider=True,
            fallback_used=True,
        )


def _to_document_read(document) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        title=document.title,
        source_uri=document.source_uri,
        mime_type=document.mime_type,
        status=document.status,
        metadata=document.meta,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _derive_health_status(checks: list[HealthCheck]) -> str:
    if all(c.status == "ok" for c in checks):
        return "ok"
    if any(c.status == "failed" for c in checks):
        return "failed"
    return "degraded"


def _dependency_checks(db: Session) -> list[HealthCheck]:
    checks: list[HealthCheck] = []

    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
        checks.append(HealthCheck(name="database", status="ok", detail="database reachable"))
    except Exception as exc:  # pragma: no cover - integration-dependent
        checks.append(HealthCheck(name="database", status="failed", detail=str(exc)))

    vector_extension = False
    if db_ok:
        try:
            row = db.execute(text("SELECT extname FROM pg_extension WHERE extname='vector' LIMIT 1")).first()
            if row:
                vector_extension = True
                checks.append(
                    HealthCheck(name="pgvector_extension", status="ok", detail="vector extension enabled")
                )
            else:
                checks.append(
                    HealthCheck(name="pgvector_extension", status="degraded", detail="vector extension missing")
                )
        except Exception as exc:  # pragma: no cover - integration-dependent
            checks.append(HealthCheck(name="pgvector_extension", status="failed", detail=str(exc)))

    if db_ok and vector_extension:
        try:
            similarity = db.execute(
                text("SELECT '[1,0,0]'::vector <=> '[1,0,0]'::vector AS distance")
            ).scalar_one()
            checks.append(
                HealthCheck(
                    name="pgvector_similarity",
                    status="ok",
                    detail=f"vector similarity query ok (distance={float(similarity):.4f})",
                )
            )
        except Exception as exc:  # pragma: no cover - integration-dependent
            checks.append(HealthCheck(name="pgvector_similarity", status="failed", detail=str(exc)))
    else:
        checks.append(
            HealthCheck(
                name="pgvector_similarity",
                status="degraded",
                detail="skipped because database or extension check failed",
            )
        )

    return checks


def _to_eval_result_read(run: EvalRun) -> EvalResultRead:
    status_value = run.status.value if hasattr(run.status, "value") else str(run.status)
    dataset = str((run.config or {}).get("dataset", "unknown"))
    failed_cases: list[FailedEvalCase] = []
    for item in run.results:
        if item.passed:
            continue
        metrics = item.metrics or {}
        failed_cases.append(
            FailedEvalCase(
                case_id=item.case_id,
                case_name=item.case.name if item.case else str(item.case_id),
                query=item.case.input_query if item.case else "",
                reasons=list(metrics.get("failure_reasons", [])),
                metrics=metrics,
            )
        )

    return EvalResultRead(
        eval_run_id=run.id,
        name=run.name,
        dataset=dataset,
        status=status_value,
        summary=run.summary or {},
        failed_cases=failed_cases,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


@router.get("/settings/providers", response_model=ProviderSettingsResponse)
async def get_provider_settings(
    request_metadata: RequestMetadata = Depends(get_request_metadata),
) -> ProviderSettingsResponse:
    settings = get_settings()
    logger.info(
        "provider_settings_read",
        extra={
            "request_id": request_metadata.request_id,
            "trace_id": request_metadata.trace_id,
        },
    )
    return _provider_settings_response(settings)


@router.put("/settings/providers", response_model=ProviderSettingsResponse)
async def update_provider_settings(
    payload: ProviderSettingsUpdateRequest,
    request_metadata: RequestMetadata = Depends(get_request_metadata),
) -> ProviderSettingsResponse:
    settings = get_settings()
    _apply_runtime_provider_settings(settings, payload)
    response = _provider_settings_response(settings)
    logger.info(
        "provider_settings_updated",
        extra={
            "request_id": request_metadata.request_id,
            "trace_id": request_metadata.trace_id,
            "llm_enabled": response.llm.enabled,
            "llm_has_api_key": response.llm.has_api_key,
            "reranker_enabled": response.reranker.enabled,
            "reranker_has_api_key": response.reranker.has_api_key,
        },
    )
    return response


@router.post("/settings/providers/check", response_model=ProviderCheckResponse)
async def check_provider_connectivity(
    payload: ProviderCheckRequest | None = None,
    request_metadata: RequestMetadata = Depends(get_request_metadata),
) -> ProviderCheckResponse:
    settings = get_settings()
    target: ProviderTarget = payload.target if payload else "all"
    checks: list[ProviderCheckItem] = []

    if target in ("llm", "all"):
        checks.append(await _run_llm_provider_check(settings=settings, request_metadata=request_metadata))
    if target in ("reranker", "all"):
        checks.append(await _run_reranker_provider_check(settings=settings, request_metadata=request_metadata))

    status_value = _derive_provider_check_status(checks)
    logger.info(
        "provider_connectivity_checked",
        extra={
            "request_id": request_metadata.request_id,
            "trace_id": request_metadata.trace_id,
            "target": target,
            "status": status_value,
        },
    )
    return ProviderCheckResponse(status=status_value, checks=checks)


@router.post("/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    metadata_json: str | None = Form(default=None),
    db: Session = Depends(get_db),
    request_metadata: RequestMetadata = Depends(get_request_metadata),
) -> DocumentRead:
    metadata: dict = {}
    if metadata_json:
        try:
            metadata = json.loads(metadata_json)
            if not isinstance(metadata, dict):
                raise ValueError("metadata_json must be an object")
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"invalid metadata_json: {exc}") from exc

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty file is not allowed")

    ingestion = SimpleDocumentIngestionService(db)
    try:
        document = ingestion.create_document(
            title=title,
            filename=file.filename or "uploaded.txt",
            mime_type=file.content_type,
            content_bytes=content,
            metadata=metadata,
            request_id=request_metadata.request_id,
            trace_id=request_metadata.trace_id,
        )
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _to_document_read(document)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    ingestion = SimpleDocumentIngestionService(db)
    rows, total = ingestion.list_documents(limit=limit, offset=offset)
    return DocumentListResponse(items=[_to_document_read(doc) for doc in rows], total=total)


@router.post("/documents/{id}/index", response_model=DocumentIndexResponse)
async def index_document(
    id: UUID,
    payload: DocumentIndexRequest,
    db: Session = Depends(get_db),
    request_metadata: RequestMetadata = Depends(get_request_metadata),
) -> DocumentIndexResponse:
    settings = get_settings()
    chunker = SlidingWindowChunker(chunk_size=payload.chunk_size, chunk_overlap=payload.chunk_overlap)
    embedder = DeterministicEmbedder(dimension=settings.vector_dim)
    vector_index = PgVectorIndex(db=db, settings=settings)

    indexing_service = DocumentIndexingService(
        db=db,
        chunker=chunker,
        embedder=embedder,
        vector_index=vector_index,
        settings=settings,
    )

    try:
        chunk_count, vector_count = await indexing_service.index_document(
            document_id=id,
            embedding_model=payload.embedding_model,
            request_id=request_metadata.request_id,
            timeout_seconds=settings.embedding_timeout_seconds,
            trace_id=request_metadata.trace_id,
        )
    except ValueError as exc:
        if str(exc) == "document_not_found":
            raise HTTPException(status_code=404, detail="document not found") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DocumentIndexResponse(
        document_id=id,
        status="indexed",
        chunk_count=chunk_count,
        vector_count=vector_count,
    )


@router.post("/chat/query", response_model=ChatQueryResponse)
async def query_chat(
    payload: ChatQueryRequest,
    db: Session = Depends(get_db),
    request_metadata: RequestMetadata = Depends(get_request_metadata),
) -> ChatQueryResponse:
    settings = get_settings()

    embedder = DeterministicEmbedder(dimension=settings.vector_dim)
    vector_index = PgVectorIndex(db=db, settings=settings)
    repository = RetrievalRepository(vector_index=vector_index, db=db)
    retriever = PgVectorRetriever(embedder=embedder, repository=repository, settings=settings)
    reranker = build_reranker(settings=settings)
    citation_assembler = BasicCitationAssembler()
    answer_generator = build_answer_generator(settings=settings)
    policy = DefaultAgentPolicy()
    rewrite_strategy = DefaultQueryRewriteStrategy()
    agent_executor = FiniteStateAgentExecutor(
        db=db,
        settings=settings,
        retriever=retriever,
        reranker=reranker,
        citation_assembler=citation_assembler,
        answer_generator=answer_generator,
        policy=policy,
        rewrite_strategy=rewrite_strategy,
    )

    service = RAGChatService(
        db=db,
        agent_executor=agent_executor,
    )

    try:
        session, message, retrieved, answer, _trace_id = await service.ask(
            session_id=payload.session_id,
            query=payload.query,
            top_k=payload.top_k,
            score_threshold=payload.score_threshold,
            embedding_model=payload.embedding_model,
            request_id=request_metadata.request_id,
            trace_id=request_metadata.trace_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    citations = [
        Citation(
            chunk_id=item.chunk_id,
            document_id=item.document_id,
            quote=item.quote,
            score=item.score,
            span=CitationSpan(start_char=item.start_char, end_char=item.end_char),
        )
        for item in answer.citations
    ]

    retrieval_results = [
        RetrievalResult(
            chunk_id=item.chunk.chunk_id,
            document_id=item.chunk.document_id,
            score=item.score,
            distance=item.distance,
            content_preview=item.chunk.content[:160],
        )
        for item in retrieved
    ]

    return ChatQueryResponse(
        session_id=session.id,
        message_id=message.id,
        answer=answer.text,
        citations=citations,
        retrieval_results=retrieval_results,
        abstained=answer.abstained,
        reason=answer.reason,
        created_at=message.created_at,
    )


@router.get("/chat/{id}/trace", response_model=TraceRead)
async def get_chat_trace(
    id: UUID,
    db: Session = Depends(get_db),
) -> TraceRead:
    trace = (
        db.query(AgentTrace)
        .filter(AgentTrace.session_id == id)
        .order_by(AgentTrace.started_at.desc())
        .first()
    )
    if trace is None:
        raise HTTPException(status_code=404, detail="trace_not_found")

    steps = sorted(trace.steps, key=lambda item: item.step_order)
    return TraceRead(
        trace_id=trace.id,
        session_id=trace.session_id,
        status=trace.status.value if hasattr(trace.status, "value") else str(trace.status),
        start_state=trace.start_state,
        end_state=trace.end_state,
        started_at=trace.started_at,
        finished_at=trace.finished_at,
        steps=[
            TraceStepRead(
                step_order=step.step_order,
                state=step.state,
                action=step.action,
                status=step.status.value if hasattr(step.status, "value") else str(step.status),
                input_payload=step.input_payload,
                output_payload=step.output_payload,
                input_summary=step.input_payload.get("summary"),
                output_summary=step.output_payload.get("summary"),
                fallback=bool(step.output_payload.get("fallback", False)),
                latency_ms=step.latency_ms,
                error_message=step.error_message,
                created_at=step.created_at,
            )
            for step in steps
        ],
    )


@router.post("/evals/run", response_model=EvalRunResponse)
async def run_eval(
    payload: EvalRunRequest,
    db: Session = Depends(get_db),
    request_metadata: RequestMetadata = Depends(get_request_metadata),
) -> EvalRunResponse:
    settings = get_settings()
    run = EvalRun(
        id=uuid.uuid4(),
        name=payload.name or f"eval-{payload.dataset}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        status=EvalRunStatus.QUEUED,
        triggered_by="api",
        config={"dataset": payload.dataset, **payload.config},
        summary={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    runner = PgEvaluationRunner(db=db, settings=settings)
    await runner.run(run_id=run.id)
    db.refresh(run)

    status_value = run.status.value if hasattr(run.status, "value") else str(run.status)
    accepted = bool((run.summary or {}).get("gate_passed", False))
    logger.info(
        "eval_run_requested",
        extra={
            "request_id": request_metadata.request_id,
            "trace_id": request_metadata.trace_id,
            "eval_run_id": str(run.id),
            "status": status_value,
            "accepted": accepted,
        },
    )

    return EvalRunResponse(
        eval_run_id=run.id,
        status=status_value,
        accepted=accepted,
        summary=run.summary or {},
    )


@router.get("/evals/latest", response_model=EvalResultRead)
async def get_latest_eval_result(
    db: Session = Depends(get_db),
) -> EvalResultRead:
    run = db.query(EvalRun).order_by(EvalRun.started_at.desc()).first()
    if run is None:
        raise HTTPException(status_code=404, detail="eval_run_not_found")

    return _to_eval_result_read(run)


@router.get("/evals/{id}", response_model=EvalResultRead)
async def get_eval_result(
    id: UUID,
    db: Session = Depends(get_db),
) -> EvalResultRead:
    run = db.get(EvalRun, id)
    if run is None:
        raise HTTPException(status_code=404, detail="eval_run_not_found")

    return _to_eval_result_read(run)


@router.get("/health", response_model=HealthResponse)
async def health(
    db: Session = Depends(get_db),
    request_metadata: RequestMetadata = Depends(get_request_metadata),
) -> HealthResponse:
    checks = _dependency_checks(db)
    status_value = _derive_health_status(checks)
    logger.info(
        "health_check",
        extra={
            "status": status_value,
            "request_id": request_metadata.request_id,
            "trace_id": request_metadata.trace_id,
        },
    )
    return HealthResponse(
        status=status_value,
        service="agentic-rag-backend",
        timestamp=datetime.now(UTC),
        checks=checks,
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready(
    db: Session = Depends(get_db),
    request_metadata: RequestMetadata = Depends(get_request_metadata),
) -> ReadyResponse:
    checks = _dependency_checks(db)
    status_value = _derive_health_status(checks)
    logger.info(
        "ready_check",
        extra={
            "status": status_value,
            "request_id": request_metadata.request_id,
            "trace_id": request_metadata.trace_id,
        },
    )
    metrics_snapshot = metrics.snapshot()
    summary = {
        "request_count": str(metrics_snapshot["request_count"]),
        "error_count": str(metrics_snapshot["error_count"]),
        "abstain_ratio": str(metrics_snapshot["abstain_ratio"]),
        "fallback_ratio": str(metrics_snapshot["fallback_ratio"]),
    }
    return ReadyResponse(status=status_value, checks=checks, summary=summary)
