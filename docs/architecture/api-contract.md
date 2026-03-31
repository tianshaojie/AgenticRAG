# API Contract (Step 4)

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

## 7. GET /ready

Response: `ReadyResponse`

- includes database and pgvector checks

## OpenAPI

- `GET /openapi.json`
- `GET /docs`
