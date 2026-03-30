from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EvalRunRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    dataset: str = Field(min_length=1, max_length=128)
    config: dict[str, Any] = Field(default_factory=dict)


class EvalRunResponse(BaseModel):
    eval_run_id: UUID
    status: str
    accepted: bool


class EvalResultRead(BaseModel):
    eval_run_id: UUID
    status: str
    summary: dict[str, Any]
    started_at: datetime
    finished_at: datetime | None = None
