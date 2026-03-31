# Backend (Step 4 Finite-State Agent Policy)

## 1. Install

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## 2. Start PostgreSQL + pgvector

Option A (docker):

```bash
../scripts/postgres-up.sh
```

Option B (existing PostgreSQL):

```sql
CREATE DATABASE agentic_rag;
\c agentic_rag
CREATE EXTENSION IF NOT EXISTS vector;
```

## 3. Configure env

```bash
cp .env.example .env
# ensure RAG_DATABASE_URL points to your postgres
```

## 4. Run migrations

```bash
alembic upgrade head
```

## 5. Run API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 6. API smoke curl

### Upload document (txt/md)

```bash
curl -X POST http://127.0.0.1:8000/documents \
  -F "title=Policy" \
  -F 'metadata_json={"team":"ops"}' \
  -F "file=@./sample.md;type=text/markdown"
```

### List documents

```bash
curl http://127.0.0.1:8000/documents
```

### Index document

```bash
curl -X POST http://127.0.0.1:8000/documents/<DOCUMENT_ID>/index \
  -H 'Content-Type: application/json' \
  -d '{"embedding_model":"deterministic-local-v1","chunk_size":512,"chunk_overlap":64}'
```

### Query chat

```bash
curl -X POST http://127.0.0.1:8000/chat/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the policy?","top_k":5,"score_threshold":0.25,"embedding_model":"deterministic-local-v1"}'
```

### Get latest trace by session id

```bash
curl http://127.0.0.1:8000/chat/<SESSION_ID>/trace
```

### Health and ready

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

## 7. Tests

```bash
pytest -q tests
pytest -q tests -m integration
pytest -q tests/test_smoke.py
```

## Notes

- Default `VectorIndex` implementation is PostgreSQL + pgvector (`PgVectorIndex`).
- Retrieval uses top-k by vector distance, then score threshold filtering.
- Answers always include `citations`; if evidence threshold not met, response is `abstained=true`.
- Current answer generation is deterministic local logic, not a real external LLM provider.
