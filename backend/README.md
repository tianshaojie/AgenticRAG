# Backend Guide

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

## Database and Migration

From repository root:

```bash
make db-setup
```

## Run API

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test and Eval

```bash
cd backend
source .venv/bin/activate
pytest -q tests
pytest -q tests/test_smoke.py
python -m app.evals.cli --dataset golden_v1 --name local-eval
```

## LLM Provider Toggle

`ThresholdAnswerGenerator` now supports provider injection through factory wiring.

1. Mock provider (default)

```bash
RAG_ENABLE_REAL_LLM_PROVIDER=false
```

2. Real OpenAI-compatible provider

```bash
RAG_ENABLE_REAL_LLM_PROVIDER=true
RAG_LLM_PROVIDER=openai_compatible
RAG_LLM_API_KEY=your_real_key
# full endpoint mode (recommended for current upstream)
RAG_LLM_ENDPOINT=https://agent.cnht.com.cn/v1/chat/completions
RAG_LLM_BASE_URL=
```

Or base URL + path mode:

```bash
RAG_LLM_BASE_URL=https://agent.cnht.com.cn
RAG_LLM_ENDPOINT=/v1/chat/completions
```

## Reranker Provider Toggle

1. Disable reranking hook

```bash
RAG_ENABLE_RERANKING=false
```

2. Enable reranking hook with local mock provider (default)

```bash
RAG_ENABLE_RERANKING=true
RAG_ENABLE_REAL_RERANKER_PROVIDER=false
```

3. Enable real HTTP reranker provider

```bash
RAG_ENABLE_RERANKING=true
RAG_ENABLE_REAL_RERANKER_PROVIDER=true
RAG_RERANKER_PROVIDER=http
RAG_RERANKER_API_KEY=your_real_key
RAG_RERANKER_APP_CODE=chatbi_reranker
RAG_RERANKER_APP_NAME=妙查-重排
RAG_RERANKER_MODEL=qwen3-reranker-8b
RAG_RERANKER_INSTRUCT=Please rerank the documents based on the query.

# full endpoint mode
RAG_RERANKER_ENDPOINT=https://your-reranker-host/v1/rerank
RAG_RERANKER_BASE_URL=
```

Or base URL + path mode:

```bash
RAG_RERANKER_BASE_URL=https://your-reranker-host
RAG_RERANKER_ENDPOINT=/v1/rerank
```

## Useful Endpoints

1. `GET /docs`
2. `GET /health`
3. `GET /ready`
4. `POST /documents`
5. `POST /documents/{id}/index`
6. `POST /chat/query`
7. `GET /chat/{id}/trace`
8. `POST /evals/run`
9. `GET /evals/latest`
