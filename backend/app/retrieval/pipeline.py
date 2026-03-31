from __future__ import annotations

import logging

from app.core.errors import AppError
from app.domain.interfaces import CitationAssembler, Reranker, Retriever, ScoredChunk


class RetrievalPipeline:
    """Two-stage retrieval pipeline skeleton: retrieve -> rerank -> citation assemble."""

    def __init__(
        self,
        retriever: Retriever,
        reranker: Reranker,
        citation_assembler: CitationAssembler,
        *,
        enable_reranking: bool = True,
    ) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.citation_assembler = citation_assembler
        self.enable_reranking = enable_reranking
        self._logger = logging.getLogger("app.retrieval.pipeline")

    async def run(
        self,
        *,
        query: str,
        top_k: int,
        score_threshold: float,
        model: str,
        rerank_k: int,
        request_id: str = "unknown",
        trace_id: str = "unknown",
        enable_reranking: bool | None = None,
    ) -> tuple[list[ScoredChunk], list]:
        candidates = await self.retriever.retrieve(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            model=model,
        )

        should_rerank = self.enable_reranking if enable_reranking is None else enable_reranking
        if not should_rerank:
            ranked = candidates[: min(max(rerank_k, 1), len(candidates))]
        else:
            try:
                ranked = await self.reranker.rerank(
                    query=query,
                    candidates=candidates,
                    top_n=rerank_k,
                    request_id=request_id,
                    trace_id=trace_id,
                )
            except AppError as exc:
                self._logger.warning(
                    "pipeline_rerank_fallback",
                    extra={
                        "request_id": request_id,
                        "trace_id": trace_id,
                        "operation": "rerank_hook",
                        "error_code": exc.code,
                        "fallback_used": True,
                    },
                )
                ranked = candidates[: min(max(rerank_k, 1), len(candidates))]
        citations = self.citation_assembler.assemble(ranked_chunks=ranked)
        return ranked, citations
