# API Contract (Step 6)

Base URL: `http://localhost:8000`

## 1. POST /documents

`multipart/form-data`

- `title` (string, required)
- `file` (UploadFile, required, txt/md)
- `metadata_json` (stringified JSON object, optional)

Response: `DocumentRead`

## 2. GET /documents

Query params:

- `limit` (default 50)
- `offset` (default 0)

Response: `DocumentListResponse`

## 3. POST /documents/{id}/index

JSON body:

- `embedding_model`
- `chunk_size`
- `chunk_overlap`

Response: `DocumentIndexResponse`

## 4. POST /chat/query

JSON body:

- `session_id` (optional)
- `query`
- `top_k`
- `score_threshold`
- `embedding_model`

Response: `ChatQueryResponse`

- always includes `citations`
- citations include `document_id`, `chunk_id`, and `span`
- no-evidence returns `abstained=true`

## 5. GET /chat/{id}/trace

Path param:

- `id` = `session_id`

Response: `TraceRead`

- returns latest trace for the chat session
- includes ordered `steps` with per-step summary, latency, fallback, and errors

## 6. GET /health

Response: `HealthResponse`

- includes dependency `checks` (`database`, `pgvector_extension`, `pgvector_similarity`)

## 7. GET /ready

Response: `ReadyResponse`

- includes database and pgvector checks
- includes readiness `summary` (`request_count`, `error_count`, `abstain_ratio`, `fallback_ratio`)

## 8. POST /evals/run

JSON body:

- `name` (optional)
- `dataset` (default `golden_v1`)
- `config` (optional)

Response: `EvalRunResponse`

- includes `eval_run_id`
- includes `status` and `accepted` gate flag
- includes run `summary`

## 9. GET /evals/{id}

Path param:

- `id` = `eval_run_id`

Response: `EvalResultRead`

- includes run summary metrics
- includes failed case list with reasons

## 10. GET /evals/latest

Response: `EvalResultRead`

- latest eval run summary

## Error Response (All Endpoints)

On non-2xx responses, API returns stable error schema:

```json
{
  "error": {
    "code": "string",
    "category": "validation|dependency|timeout|internal|unavailable",
    "message": "string",
    "request_id": "string",
    "trace_id": "string",
    "details": {}
  }
}
```

## OpenAPI

- `GET /openapi.json`
- `GET /docs`
