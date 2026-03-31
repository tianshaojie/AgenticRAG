# Agentic RAG

Production-oriented Agentic RAG system with:

1. FastAPI + SQLAlchemy + Alembic backend
2. PostgreSQL + pgvector vector retrieval
3. Vue 3 + TypeScript frontend
4. Finite-state agent policy with persisted traces
5. Eval/regression gate for retrieval, answer, citation, and agent behavior

## 1. Prerequisites

1. Python 3.12+ (project currently runs on 3.13 in this repo environment)
2. Node.js 20+
3. Local PostgreSQL service with pgvector extension
4. GNU Make

## 2. Quick Start

```bash
git clone <your-repo-url>
cd AgenticRAG
make install
```

### Initialize databases and extension

```bash
make db-setup
```

### Run services (two terminals)

```bash
make backend-dev
make frontend-dev
```

### Access

1. Frontend: [http://localhost:5173](http://localhost:5173)
2. Backend: [http://localhost:8000](http://localhost:8000)
3. OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

## 3. PostgreSQL Initialization (Manual SQL Alternative)

If you do not use `make db-setup`, run:

```sql
CREATE DATABASE agentic_rag_dev;
CREATE DATABASE agentic_rag_test;
\c agentic_rag_dev
CREATE EXTENSION IF NOT EXISTS vector;
\c agentic_rag_test
CREATE EXTENSION IF NOT EXISTS vector;
```

## 4. Alembic Migration Commands

`make db-setup` already includes migration (`db-init + migrate`).

## 5. Backend Run Commands

```bash
cd backend
cp .env.example .env
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 6. Frontend Run Commands

```bash
cd frontend
cp .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

## 7. Test, Smoke, Eval, Build

```bash
make lint
make test
make smoke
make eval
make build
```

## 8. LLM Provider Configuration (OpenAI-Compatible)

Default mode keeps **real LLM disabled** and uses local mock provider for deterministic tests.

Core env vars (`backend/.env` with `RAG_` prefix):

1. `RAG_LLM_PROVIDER` (`openai_compatible` or `mock`)
2. `RAG_LLM_API_KEY`
3. `RAG_LLM_BASE_URL`
4. `RAG_LLM_ENDPOINT`
5. `RAG_LLM_MODEL`
6. `RAG_LLM_TIMEOUT_SECONDS`
7. `RAG_LLM_MAX_RETRIES`
8. `RAG_LLM_TEMPERATURE`
9. `RAG_LLM_MAX_TOKENS`
10. `RAG_ENABLE_REAL_LLM_PROVIDER` (`true/false`)

### Current Provider Address Configuration

Given current endpoint:

`https://agent.cnht.com.cn/v1/chat/completions`

Recommended configuration:

```bash
RAG_LLM_ENDPOINT=https://agent.cnht.com.cn/v1/chat/completions
RAG_LLM_BASE_URL=
```

Alternative (`base_url + path`) configuration:

```bash
RAG_LLM_BASE_URL=https://agent.cnht.com.cn
RAG_LLM_ENDPOINT=/v1/chat/completions
```

## 9. Switching Mock / Real Provider

Mock (default):

```bash
RAG_ENABLE_REAL_LLM_PROVIDER=false
```

Real provider:

```bash
RAG_ENABLE_REAL_LLM_PROVIDER=true
RAG_LLM_PROVIDER=openai_compatible
RAG_LLM_API_KEY=your_real_key
```

## 10. Real Provider Validation After Getting API Key

1. Set env vars above (`RAG_ENABLE_REAL_LLM_PROVIDER=true`, `RAG_LLM_API_KEY`, endpoint/base config).
2. Restart backend.
3. Upload and index a demo document.
4. Query `/chat/query` with in-domain question.
5. Verify response keeps citations and no-evidence still abstains.
6. Check `/chat/{session_id}/trace` for generation step and fallback markers.

## 10.1 Reranker Provider Configuration

Reranker defaults to mock provider and can be enabled independently.

Core env vars (`backend/.env` with `RAG_` prefix):

1. `RAG_RERANKER_PROVIDER` (`http` or `mock`)
2. `RAG_RERANKER_API_KEY`
3. `RAG_RERANKER_BASE_URL`
4. `RAG_RERANKER_ENDPOINT`
5. `RAG_RERANKER_MODEL`
6. `RAG_RERANKER_TIMEOUT_SECONDS`
7. `RAG_RERANKER_MAX_RETRIES`
8. `RAG_RERANKER_TOP_N`
9. `RAG_RERANKER_APP_CODE`
10. `RAG_RERANKER_APP_NAME`
11. `RAG_RERANKER_INSTRUCT`
12. `RAG_ENABLE_REAL_RERANKER_PROVIDER` (`true/false`)
13. `RAG_ENABLE_RERANKING` (`true/false`)

Endpoint mode examples:

```bash
# full endpoint mode
RAG_RERANKER_ENDPOINT=https://your-reranker-host/v1/rerank
RAG_RERANKER_BASE_URL=

# base_url + path mode
RAG_RERANKER_BASE_URL=https://your-reranker-host
RAG_RERANKER_ENDPOINT=/v1/rerank
```

Switching behavior:

```bash
# disable reranking hook entirely
RAG_ENABLE_RERANKING=false

# keep hook enabled, but use local deterministic mock
RAG_ENABLE_RERANKING=true
RAG_ENABLE_REAL_RERANKER_PROVIDER=false

# real HTTP reranker
RAG_ENABLE_RERANKING=true
RAG_ENABLE_REAL_RERANKER_PROVIDER=true
RAG_RERANKER_PROVIDER=http
RAG_RERANKER_API_KEY=your_real_key
```

When reranker call fails, system falls back to original pgvector retrieval order.

## 11. Demo Data

1. Demo upload documents: `evals/demo_documents/`
2. Golden eval sets:
- `evals/golden/golden_v1.json` (default CI gate)
- `evals/golden/golden_minimal.json` (minimal local smoke)

## 12. API Highlights

1. `POST /documents`
2. `GET /documents`
3. `POST /documents/{id}/index`
4. `POST /chat/query`
5. `GET /chat/{id}/trace`
6. `GET /health`
7. `GET /ready`
8. `POST /evals/run`
9. `GET /evals/{id}`
10. `GET /evals/latest`

All non-2xx errors follow stable schema:

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

## 13. Common Troubleshooting

1. Frontend shows `Network Error`:
- Confirm backend is running on `8000`.
- Confirm frontend uses `5173` build, not stale `3000` docker page.
- Check `frontend/.env` `VITE_API_BASE_URL`.

2. `pgvector` errors:
- Ensure `CREATE EXTENSION IF NOT EXISTS vector;` exists in target DB.
- Verify `/ready` contains `pgvector_extension: ok`.

3. Migration errors:
- Ensure `RAG_DATABASE_URL` points to the intended DB.
- Re-run `make db-init` then `make migrate`.

4. Eval gate fails:
- Inspect `GET /evals/latest` summary.
- Check `citation_integrity_failures`, `unsupported_answer_rate`, step/rewrite limit metrics.

5. Real LLM not taking effect:
- Confirm `RAG_ENABLE_REAL_LLM_PROVIDER=true`.
- Confirm backend process loaded updated `.env`.
- Confirm `RAG_LLM_API_KEY` is set and non-empty.

## 14. Architecture and Quality Docs

1. [Architecture Index](./docs/architecture/README.md)
2. [API Contract](./docs/architecture/api-contract.md)
3. [Database Schema](./docs/architecture/database-schema.md)
4. [pgvector Retrieval Design](./docs/architecture/pgvector-retrieval-design.md)
5. [Agent Policy](./docs/architecture/agent-policy.md)
6. [Eval Methodology](./docs/architecture/eval-methodology.md)
7. [Observability](./docs/architecture/observability.md)
8. [Release Acceptance](./docs/quality/release-acceptance.md)
