from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
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
            "http://localhost:5175",
            "http://127.0.0.1:5175",
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
    agent_conflict_score_delta: float = Field(default=0.30, ge=0.0, le=1.0)
    agent_available_routes: list[str] = Field(default=["pgvector", "sql", "api"])
    agent_sql_route_provider: Literal["lexical", "mock"] = Field(default="lexical")
    agent_api_route_provider: Literal["lexical", "mock"] = Field(default="lexical")
    agent_retrieval_stagnation_limit: int = Field(default=1, ge=1, le=8)
    agent_retrieval_min_score_gain: float = Field(default=0.02, ge=0.0, le=1.0)
    agent_filter_min_score: float = Field(default=0.30, ge=0.0, le=1.0)
    agent_max_chunks_per_document: int = Field(default=2, ge=1, le=20)

    request_timeout_seconds: int = Field(default=10, ge=1)
    request_retry_attempts: int = Field(default=2, ge=0)
    provider_backoff_base_ms: int = Field(default=100, ge=10, le=5000)
    provider_backoff_max_ms: int = Field(default=1000, ge=50, le=10000)

    embedding_timeout_seconds: int = Field(default=8, ge=1, le=120)
    embedding_retry_attempts: int = Field(default=2, ge=0, le=8)
    retrieval_timeout_seconds: int = Field(default=8, ge=1, le=120)
    retrieval_retry_attempts: int = Field(default=2, ge=0, le=8)
    rerank_timeout_seconds: int = Field(default=6, ge=1, le=120)
    rerank_retry_attempts: int = Field(default=1, ge=0, le=8)
    generation_timeout_seconds: int = Field(default=8, ge=1, le=120)
    generation_retry_attempts: int = Field(default=1, ge=0, le=8)

    reranker_provider: Literal["http", "mock"] = Field(default="http")
    reranker_api_key: SecretStr | None = Field(default=None)
    reranker_base_url: str | None = Field(default=None)
    reranker_endpoint: str | None = Field(default=None)
    reranker_model: str = Field(default="qwen3-reranker-8b")
    reranker_timeout_seconds: int = Field(default=8, ge=1, le=180)
    reranker_max_retries: int = Field(default=2, ge=0, le=8)
    reranker_top_n: int = Field(default=5, ge=1, le=100)
    reranker_app_code: str = Field(default="chatbi_reranker")
    reranker_app_name: str = Field(default="妙查-重排")
    reranker_instruct: str = Field(default="Please rerank the documents based on the query.")
    enable_real_reranker_provider: bool = Field(default=False)
    enable_reranking: bool = Field(default=True)

    llm_provider: Literal["openai_compatible", "mock"] = Field(default="openai_compatible")
    llm_api_key: SecretStr | None = Field(default=None)
    llm_base_url: str | None = Field(default=None)
    llm_endpoint: str = Field(default="https://agent.cnht.com.cn/v1/chat/completions")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_timeout_seconds: int = Field(default=15, ge=1, le=180)
    llm_max_retries: int = Field(default=2, ge=0, le=8)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=512, ge=1, le=4096)
    enable_real_llm_provider: bool = Field(default=False)

    eval_dataset_dir: str = Field(default="../evals/golden")
    eval_default_dataset: str = Field(default="golden_v1")
    eval_max_unsupported_answer_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    eval_warning_unsupported_answer_rate: float = Field(default=0.05, ge=0.0, le=1.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
