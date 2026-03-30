from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class TraceStepRead(BaseModel):
    step_order: int
    state: str
    action: str
    status: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    latency_ms: int | None = None
    error_message: str | None = None
    created_at: datetime


class TraceRead(BaseModel):
    trace_id: UUID
    session_id: UUID
    status: str
    start_state: str
    end_state: str | None = None
    steps: list[TraceStepRead]
    started_at: datetime
    finished_at: datetime | None = None
