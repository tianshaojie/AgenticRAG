# Step 2 Backend Minimal RAG Loop

## Data Flow

1. `POST /documents` uploads txt/md content.
2. Ingestion persists:
   - `documents`
   - `document_versions` (with `content_text`)
3. `POST /documents/{id}/index`:
   - read latest `document_versions.content_text`
   - chunk via sliding window
   - write `document_chunks`
   - deterministic embedder generates vectors
   - upsert vectors into `chunk_vectors`
4. `POST /chat/query`:
   - embed query
   - pgvector top-k retrieval from `chunk_vectors` + `document_chunks`
   - score-threshold filtering
   - citation assembly (doc/chunk/span)
   - evidence threshold check
   - answer generation or abstain
   - persist chat messages

## PostgreSQL / pgvector Strategy

- Extension: `CREATE EXTENSION IF NOT EXISTS vector`
- Vector storage table: `chunk_vectors`
- Vector column: `chunk_vectors.embedding VECTOR(1536)`
- Mapping: `chunk_vectors.chunk_id -> document_chunks.id`
- Indexing (migration):
  - `ivfflat` index on embedding (`vector_cosine_ops`)
  - btree index on `chunk_id`
  - GIN index on metadata JSONB
- Retrieval behavior:
  - primary ordering by vector distance
  - score computed from distance (`cosine: score = 1 - distance`)
  - threshold applied after retrieval scan

## Current Retrieval Execution Characteristics

- ANN index structure is created (`ivfflat`) in migration.
- Current query path is top-k vector ordering with optional metadata filters.
- Rerank stage is intentionally not implemented in Step 2.
