from __future__ import annotations

import logging
import re

from app.core.errors import AppError
from app.domain.interfaces import Reranker, ScoredChunk
from app.reranker.interfaces import RerankRequest, RerankerCandidate, RerankerProvider


class BasicReranker(Reranker):
    """Simple lexical+vector reranker for local deterministic baseline."""

    @staticmethod
    def _terms(text: str) -> list[str]:
        terms = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+", text.lower())
        return terms[:16]

    async def rerank(
        self,
        *,
        query: str,
        candidates: list[ScoredChunk],
        top_n: int,
        request_id: str = "unknown",
        trace_id: str = "unknown",
    ) -> list[ScoredChunk]:
        _ = request_id, trace_id
        if not candidates:
            return []

        terms = self._terms(query)
        if not terms:
            return candidates[:top_n]

        def combined_score(item: ScoredChunk) -> float:
            content = item.chunk.content.lower()
            lexical_hits = sum(1 for term in terms if term in content)
            lexical_score = lexical_hits / len(terms)
            return 0.65 * item.score + 0.35 * lexical_score

        ranked = sorted(candidates, key=combined_score, reverse=True)
        return ranked[:top_n]


class ProviderBackedReranker(Reranker):
    """Optional rerank hook: pgvector retrieval -> provider rerank -> fallback to retrieval order."""

    def __init__(
        self,
        *,
        provider: RerankerProvider,
        enable_reranking: bool,
        model: str,
        timeout_seconds: float,
        default_top_n: int,
        logger: logging.Logger | None = None,
    ) -> None:
        self._provider = provider
        self._enable_reranking = enable_reranking
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._default_top_n = max(default_top_n, 1)
        self._logger = logger or logging.getLogger("app.retrieval.reranker")

    @staticmethod
    def _fallback(candidates: list[ScoredChunk], *, top_n: int) -> list[ScoredChunk]:
        return candidates[: min(max(top_n, 1), len(candidates))]

    async def rerank(
        self,
        *,
        query: str,
        candidates: list[ScoredChunk],
        top_n: int,
        request_id: str = "unknown",
        trace_id: str = "unknown",
    ) -> list[ScoredChunk]:
        if not candidates:
            return []

        limit = min(max(top_n, 1), len(candidates)) if top_n > 0 else min(self._default_top_n, len(candidates))
        if not self._enable_reranking:
            return self._fallback(candidates, top_n=limit)

        provider_request = RerankRequest(
            query=query,
            candidates=[
                RerankerCandidate(
                    candidate_id=str(item.chunk.chunk_id),
                    document=item.chunk.content,
                    metadata={
                        "document_id": str(item.chunk.document_id),
                        "chunk_index": item.chunk.chunk_index,
                    },
                )
                for item in candidates
            ],
            top_n=limit,
            model=self._model,
            timeout_seconds=self._timeout_seconds,
            request_id=request_id,
            trace_id=trace_id,
        )

        try:
            response = await self._provider.rerank(request=provider_request)
        except AppError as exc:
            self._logger.warning(
                "rerank_hook_fallback_to_retrieval",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "provider_name": type(self._provider).__name__,
                    "operation": "rerank_hook",
                    "error_code": exc.code,
                    "fallback_used": True,
                },
            )
            return self._fallback(candidates, top_n=limit)

        by_id = {str(item.chunk.chunk_id): item for item in candidates}
        ordered: list[ScoredChunk] = []
        seen: set[str] = set()
        for ranked_item in sorted(response.items, key=lambda item: item.rank):
            candidate = by_id.get(ranked_item.candidate_id)
            if candidate is None or ranked_item.candidate_id in seen:
                continue
            seen.add(ranked_item.candidate_id)
            ordered.append(candidate)
            if len(ordered) >= limit:
                break

        if len(ordered) < limit:
            self._logger.warning(
                "rerank_hook_partial_fallback",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "provider_name": type(self._provider).__name__,
                    "operation": "rerank_hook",
                    "fallback_used": True,
                },
            )
            for item in candidates:
                candidate_id = str(item.chunk.chunk_id)
                if candidate_id in seen:
                    continue
                seen.add(candidate_id)
                ordered.append(item)
                if len(ordered) >= limit:
                    break

        return ordered
