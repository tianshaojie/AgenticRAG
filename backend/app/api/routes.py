from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, status

from app.api.deps import get_request_metadata
from app.domain.enums import DocumentStatus
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from app.schemas.common import HealthResponse, ReadyResponse, RequestMetadata
from app.schemas.documents import (
    DocumentCreateRequest,
    DocumentIndexRequest,
    DocumentIndexResponse,
    DocumentListResponse,
    DocumentRead,
)
from app.schemas.evals import EvalResultRead, EvalRunRequest, EvalRunResponse
from app.schemas.traces import TraceRead, TraceStepRead

router = APIRouter()


@router.post("/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreateRequest,
    metadata: RequestMetadata = Depends(get_request_metadata),
) -> DocumentRead:
    now = datetime.now(UTC)
    return DocumentRead(
        id=uuid4(),
        title=payload.title,
        source_uri=payload.source_uri,
        mime_type=payload.mime_type,
        status=DocumentStatus.RECEIVED,
        metadata={"request_id": metadata.request_id, **payload.metadata},
        created_at=now,
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    return DocumentListResponse(items=[], total=0)


@router.post(
    "/documents/{id}/index",
    response_model=DocumentIndexResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def index_document(id: UUID, payload: DocumentIndexRequest) -> DocumentIndexResponse:
    _ = payload
    return DocumentIndexResponse(document_id=id, status="queued", accepted=True)


@router.post("/chat/query", response_model=ChatQueryResponse)
async def query_chat(
    payload: ChatQueryRequest,
    metadata: RequestMetadata = Depends(get_request_metadata),
) -> ChatQueryResponse:
    _ = payload
    now = datetime.now(UTC)
    return ChatQueryResponse(
        session_id=payload.session_id or uuid4(),
        message_id=uuid4(),
        trace_id=uuid4(),
        answer="Insufficient evidence to answer reliably. Please ingest and index relevant documents.",
        citations=[],
        abstained=True,
        reason=f"no_retrieved_evidence; request_id={metadata.request_id}",
        created_at=now,
    )


@router.get("/chat/{id}/trace", response_model=TraceRead)
async def get_chat_trace(id: UUID) -> TraceRead:
    now = datetime.now(UTC)
    return TraceRead(
        trace_id=uuid4(),
        session_id=id,
        status="running",
        start_state="RECEIVED",
        end_state=None,
        steps=[
            TraceStepRead(
                step_order=1,
                state="RECEIVED",
                action="accept_query",
                status="success",
                input_payload={},
                output_payload={},
                created_at=now,
            )
        ],
        started_at=now,
        finished_at=None,
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="agentic-rag-backend", timestamp=datetime.now(UTC))


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    return ReadyResponse(status="degraded", checks={"database": "not_checked", "vector": "not_checked"})


@router.post("/evals/run", response_model=EvalRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_eval(payload: EvalRunRequest) -> EvalRunResponse:
    _ = payload
    return EvalRunResponse(eval_run_id=uuid4(), status="queued", accepted=True)


@router.get("/evals/{id}", response_model=EvalResultRead)
async def get_eval(id: UUID) -> EvalResultRead:
    return EvalResultRead(
        eval_run_id=id,
        status="queued",
        summary={},
        started_at=datetime.now(UTC),
        finished_at=None,
    )
