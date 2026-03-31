# pgvector Retrieval Design

## Objective

Provide deterministic, replaceable vector retrieval with PostgreSQL + pgvector as the default `VectorIndex`.

## Data Placement

1. Text and span data live in `document_chunks`.
2. Embeddings live in `chunk_vectors.embedding`.
3. Relation is `chunk_vectors.chunk_id -> document_chunks.id`.

This split keeps chunk text lifecycle independent from embedding model lifecycle.

## Distance Metric

Default metric: `cosine` distance.

- Operator: `<=>`
- Smaller distance means closer vector.
- API-facing score is normalized in retrieval service.

## Retrieval Path

1. Embed query via `Embedder`.
2. Execute `top_k` vector lookup in `PgVectorIndex`.
3. Apply score threshold filtering in retriever service.
4. Optional lexical fallback when vector stage fails or yields empty.
5. Return stable `RetrievalResult` schema.

## Query Pattern

Representative SQL shape:

```sql
SELECT
  cv.chunk_id,
  dc.document_id,
  dc.content,
  (cv.embedding <=> :query_vector) AS distance
FROM chunk_vectors cv
JOIN document_chunks dc ON dc.id = cv.chunk_id
WHERE cv.embedding_model = :embedding_model
ORDER BY cv.embedding <=> :query_vector
LIMIT :top_k;
```

## ANN vs Exact

Current implementation has ANN structure pre-created using IVFFlat index (`lists = 100`), but practical behavior still depends on dataset size and planner choices.

- Small datasets may behave close to exact scan.
- Larger datasets benefit from IVFFlat.
- Next-stage optimization should benchmark with production-scale rows before tuning `lists/probes`.

## Metadata Filter Extension

Current extensibility uses JSONB metadata + GIN indexes.  
For high-selectivity fields (`tenant_id`, `language`, `document_type`), add explicit columns and btree indexes.

## Rerank Cooperation

1. Retrieval stage: high recall candidate pool from pgvector.
2. Rerank stage: precision refinement on candidate set.
3. Citation assembly: derive evidence spans from reranked chunks.
4. Answer generation: answer only with sufficient citations, otherwise abstain.
