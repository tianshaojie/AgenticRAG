from __future__ import annotations

from app.domain.interfaces import CitationAssembler, Reranker, Retriever, ScoredChunk


class RetrievalPipeline:
    """Two-stage retrieval pipeline skeleton: retrieve -> rerank -> citation assemble."""

    def __init__(self, retriever: Retriever, reranker: Reranker, citation_assembler: CitationAssembler) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.citation_assembler = citation_assembler

    async def run(
        self,
        *,
        query: str,
        top_k: int,
        score_threshold: float,
        model: str,
        rerank_k: int,
    ) -> tuple[list[ScoredChunk], list]:
        candidates = await self.retriever.retrieve(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            model=model,
        )
        ranked = await self.reranker.rerank(query=query, candidates=candidates, top_n=rerank_k)
        citations = self.citation_assembler.assemble(ranked_chunks=ranked)
        return ranked, citations
