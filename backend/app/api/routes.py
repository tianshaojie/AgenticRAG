from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_metadata
from app.agent.executor import FiniteStateAgentExecutor
from app.agent.policy import DefaultAgentPolicy
from app.agent.rewrite import DefaultQueryRewriteStrategy
from app.core.config import get_settings
from app.db.models import AgentTrace
from app.ingestion.service import SimpleDocumentIngestionService, UnsupportedDocumentError
from app.indexing.chunker import SlidingWindowChunker
from app.indexing.embedder import DeterministicEmbedder
from app.indexing.pgvector_index import PgVectorIndex
from app.indexing.service import DocumentIndexingService
from app.retrieval.reranker import BasicReranker
from app.retrieval.repository import RetrievalRepository
from app.retrieval.service import PgVectorRetriever
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from app.schemas.common import Citation, CitationSpan, HealthCheck, HealthResponse, ReadyResponse, RequestMetadata
from app.schemas.documents import DocumentIndexRequest, DocumentIndexResponse, DocumentListResponse, DocumentRead
from app.schemas.retrieval import RetrievalResult
from app.schemas.traces import TraceRead, TraceStepRead
from app.services.answer import ThresholdAnswerGenerator
from app.services.citation import BasicCitationAssembler
from app.services.rag_chat import RAGChatService

router = APIRouter()
logger = logging.getLogger("app.api")


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
    )

    try:
        chunk_count, vector_count = await indexing_service.index_document(
            document_id=id,
            embedding_model=payload.embedding_model,
            request_id=request_metadata.request_id,
            timeout_seconds=settings.request_timeout_seconds,
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
    reranker = BasicReranker()
    citation_assembler = BasicCitationAssembler()
    answer_generator = ThresholdAnswerGenerator(
        min_citations=settings.evidence_min_citations,
        min_score=settings.evidence_min_score,
    )
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


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="agentic-rag-backend", timestamp=datetime.now(UTC))


@router.get("/ready", response_model=ReadyResponse)
async def ready(
    db: Session = Depends(get_db),
    request_metadata: RequestMetadata = Depends(get_request_metadata),
) -> ReadyResponse:
    checks: list[HealthCheck] = []

    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
        checks.append(HealthCheck(name="database", status="ok", detail="database reachable"))
    except Exception as exc:  # pragma: no cover - integration-dependent
        checks.append(HealthCheck(name="database", status="failed", detail=str(exc)))

    if db_ok:
        try:
            row = db.execute(text("SELECT extname FROM pg_extension WHERE extname='vector' LIMIT 1")).first()
            if row:
                checks.append(HealthCheck(name="pgvector", status="ok", detail="vector extension enabled"))
            else:
                checks.append(
                    HealthCheck(name="pgvector", status="degraded", detail="vector extension missing")
                )
        except Exception as exc:  # pragma: no cover - integration-dependent
            checks.append(HealthCheck(name="pgvector", status="failed", detail=str(exc)))

    if all(c.status == "ok" for c in checks):
        status_value = "ok"
    elif any(c.status == "failed" for c in checks):
        status_value = "failed"
    else:
        status_value = "degraded"

    logger.info("ready_check", extra={"status": status_value, "request_id": request_metadata.request_id})
    return ReadyResponse(status=status_value, checks=checks)
