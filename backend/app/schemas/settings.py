from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


HealthStatus = Literal["ok", "degraded", "failed"]
ProviderTarget = Literal["llm", "reranker", "all"]


class ProviderRuntimeConfig(BaseModel):
    name: Literal["llm", "reranker"]
    provider: str
    enabled: bool
    has_api_key: bool
    api_key_last4: str | None = None
    endpoint: str | None = None
    base_url: str | None = None
    model: str | None = None
    timeout_seconds: int
    max_retries: int


class ProviderSettingsResponse(BaseModel):
    llm: ProviderRuntimeConfig
    reranker: ProviderRuntimeConfig
    note: str = Field(
        default="api keys are runtime-only and will be reset after backend restart"
    )


class ProviderSettingsUpdateRequest(BaseModel):
    llm_api_key: str | None = None
    reranker_api_key: str | None = None
    llm_endpoint: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    reranker_endpoint: str | None = None
    reranker_base_url: str | None = None
    reranker_model: str | None = None
    enable_real_llm_provider: bool | None = None
    enable_real_reranker_provider: bool | None = None


class ProviderCheckRequest(BaseModel):
    target: ProviderTarget = "all"


class ProviderCheckItem(BaseModel):
    provider: Literal["llm", "reranker"]
    status: HealthStatus
    detail: str
    checked_at: datetime
    latency_ms: float | None = None
    used_real_provider: bool
    fallback_used: bool = False


class ProviderCheckResponse(BaseModel):
    status: HealthStatus
    checks: list[ProviderCheckItem]
