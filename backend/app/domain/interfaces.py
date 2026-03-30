from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


@dataclass(slots=True)
class ChunkRecord:
    chunk_id: UUID
    document_id: UUID
    content: str
    chunk_index: int
    metadata: dict[str, Any]


@dataclass(slots=True)
class ScoredChunk:
    chunk: ChunkRecord
    score: float


@dataclass(slots=True)
class CitationRecord:
    chunk_id: UUID
    document_id: UUID
    quote: str
    score: float


@dataclass(slots=True)
class GeneratedAnswer:
    text: str
    citations: list[CitationRecord]
    abstained: bool
    reason: str | None = None


class DocumentIngestor(Protocol):
    async def ingest(self, *, document_id: UUID) -> None:
        """Load source, persist normalized document payload, and enqueue chunking."""


class Chunker(Protocol):
    def chunk(self, *, text: str, metadata: dict[str, Any] | None = None) -> list[ChunkRecord]:
        """Split text into deterministic chunks."""


class Embedder(Protocol):
    async def embed(self, *, inputs: list[str], model: str) -> list[list[float]]:
        """Generate embeddings with timeout/retry guards."""


class VectorIndex(Protocol):
    async def upsert(self, *, vectors: list[tuple[UUID, list[float], dict[str, Any]]]) -> None:
        """Persist vectors for chunk ids."""

    async def search(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        """Return top-k scored chunks from pgvector index."""


class Retriever(Protocol):
    async def retrieve(self, *, query: str, top_k: int) -> list[ScoredChunk]:
        """Retrieve candidate chunks via vector index and metadata filters."""


class Reranker(Protocol):
    async def rerank(self, *, query: str, candidates: list[ScoredChunk], top_n: int) -> list[ScoredChunk]:
        """Rerank candidates in second-stage ranking layer."""


class CitationAssembler(Protocol):
    def assemble(self, *, ranked_chunks: list[ScoredChunk]) -> list[CitationRecord]:
        """Convert ranked chunks into user-visible citation payloads."""


class AnswerGenerator(Protocol):
    async def generate(self, *, query: str, citations: list[CitationRecord]) -> GeneratedAnswer:
        """Generate answer from cited context or abstain when evidence is insufficient."""


class AgentPolicy(Protocol):
    def next_state(self, *, current_state: str, context: dict[str, Any]) -> str:
        """Finite-state transition policy for retrieval/synthesis flow."""


class EvaluationRunner(Protocol):
    async def run(self, *, run_id: UUID) -> None:
        """Execute deterministic evaluation run and persist metrics."""
