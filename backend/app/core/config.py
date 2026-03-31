from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RAG_", extra="ignore")

    app_name: str = Field(default="Agentic RAG")
    env: Literal["dev", "test", "staging", "prod"] = Field(default="dev")
    log_level: str = Field(default="INFO")
    cors_allowed_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    cors_allowed_methods: list[str] = Field(default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    cors_allowed_headers: list[str] = Field(default=["*"])

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/agentic_rag"
    )

    vector_dim: int = Field(default=1536, ge=128)
    vector_distance_metric: Literal["cosine", "l2", "inner_product"] = Field(default="cosine")

    default_chunk_size: int = Field(default=512, ge=64, le=4096)
    default_chunk_overlap: int = Field(default=64, ge=0, le=1024)
    default_top_k: int = Field(default=10, ge=1, le=100)
    default_score_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    evidence_min_citations: int = Field(default=1, ge=1, le=10)
    evidence_min_score: float = Field(default=0.30, ge=0.0, le=1.0)

    default_embedding_model: str = Field(default="deterministic-local-v1")
    agent_max_steps: int = Field(default=12, ge=4, le=64)
    agent_max_rewrites: int = Field(default=2, ge=0, le=6)
    agent_rerank_top_n: int = Field(default=5, ge=1, le=50)
    agent_query_min_chars: int = Field(default=2, ge=1, le=32)
    agent_min_evidence_results: int = Field(default=1, ge=1, le=20)
    agent_conflict_score_delta: float = Field(default=0.05, ge=0.0, le=1.0)

    request_timeout_seconds: int = Field(default=10, ge=1)
    request_retry_attempts: int = Field(default=2, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
