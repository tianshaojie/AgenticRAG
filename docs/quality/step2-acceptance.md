# Step 2 Acceptance Snapshot

## Implemented

- [x] Document ingestion (txt/md)
- [x] Chunking
- [x] Replaceable embedder interface + deterministic default implementation
- [x] PostgreSQL persistence
- [x] pgvector upsert + top-k retrieval + score threshold
- [x] Citation assembly with document/chunk/span mapping
- [x] Abstain fallback when evidence is insufficient
- [x] FastAPI routes for required endpoints
- [x] Alembic migration (including pgvector extension strategy)
- [x] Unit + integration + smoke tests

## Test Result Snapshot

- unit (`-m 'not integration'`): passed
- integration (`-m integration`): passed
- smoke (`tests/test_smoke.py`): passed
