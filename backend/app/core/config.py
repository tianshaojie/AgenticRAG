from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RAG_", extra="ignore")

    app_name: str = Field(default="Agentic RAG")
    env: Literal["dev", "test", "staging", "prod"] = Field(default="dev")
    log_level: str = Field(default="INFO")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/agentic_rag"
    )

    vector_dim: int = Field(default=1536, ge=128)
    vector_distance_metric: Literal["cosine", "l2", "inner_product"] = Field(default="cosine")

    request_timeout_seconds: int = Field(default=10, ge=1)
    request_retry_attempts: int = Field(default=2, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
