from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EvalRunRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    dataset: str = Field(default="golden_v1", min_length=1, max_length=128)
    config: dict[str, Any] = Field(default_factory=dict)


class EvalRunResponse(BaseModel):
    eval_run_id: UUID
    status: str
    accepted: bool
    summary: dict[str, Any] = Field(default_factory=dict)


class FailedEvalCase(BaseModel):
    case_id: UUID
    case_name: str
    query: str
    reasons: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class EvalResultRead(BaseModel):
    eval_run_id: UUID
    name: str
    dataset: str
    status: str
    summary: dict[str, Any]
    failed_cases: list[FailedEvalCase] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime | None = None
