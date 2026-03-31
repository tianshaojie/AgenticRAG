# Database Schema

Database: PostgreSQL  
Vector extension: `pgvector`

## Tables

1. `documents`
- One logical document per row.
- Key columns: `id`, `title`, `source_uri`, `status`, `metadata`, timestamps.

2. `document_versions`
- Immutable content snapshots.
- Key columns: `document_id`, `version_number`, `content_sha256`, `content_text`.
- Unique: `(document_id, version_number)`.

3. `document_chunks`
- Chunked text units generated from `document_versions`.
- Key columns: `document_id`, `document_version_id`, `chunk_index`, `content`, `start_char`, `end_char`, `metadata`.
- Unique: `(document_version_id, chunk_index)`.

4. `chunk_vectors`
- Embeddings bound to chunks and model versions.
- Key columns: `chunk_id`, `embedding_model`, `embedding_dim`, `embedding`, `metadata`.
- Unique: `(chunk_id, embedding_model)`.

5. `chat_sessions`
- Chat container.

6. `chat_messages`
- User/assistant turns with persisted citations.
- Key columns: `session_id`, `role`, `content`, `abstained`, `citations`.

7. `agent_traces`
- One finite-state execution trace for a query.
- Key columns: `session_id`, `query_text`, `status`, `start_state`, `end_state`, `request_id`, `trace_id`.

8. `agent_trace_steps`
- Step-level trace timeline.
- Key columns: `trace_id`, `step_order`, `state`, `action`, `status`, `input_payload`, `output_payload`, `latency_ms`, `error_message`.
- Unique: `(trace_id, step_order)`.

9. `eval_cases`
- Golden case definitions persisted for repeatability.

10. `eval_runs`
- One evaluation execution summary.

11. `eval_results`
- Per-case result rows for each eval run.
- Unique: `(run_id, case_id)`.

## Indexing Strategy

1. Relational query indexes
- `ix_documents_status`
- `ix_document_chunks_document_id_chunk_index`
- `ix_chat_messages_session_created`
- `ix_agent_trace_steps_trace_order`
- `ix_eval_cases_dataset_name`

2. JSON metadata indexes
- `document_chunks.metadata` GIN
- `chunk_vectors.metadata` GIN

3. pgvector index
- `ix_chunk_vectors_embedding_cosine`  
  `USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`

## Migration Notes

1. `0001_initial_schema`: base schema + `CREATE EXTENSION IF NOT EXISTS vector`.
2. `0002_content_text`: adds `document_versions.content_text`.
3. `0003_eval_case_expectations`: extends `eval_cases` for regression expectations.

Apply with:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```
