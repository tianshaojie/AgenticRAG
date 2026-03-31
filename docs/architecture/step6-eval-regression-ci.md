# Step 6: Eval, Regression, CI Gate

## Scope

Step 6 hardens the Agentic RAG lifecycle with deterministic evaluation and CI gating so quality drift is detected before release.

## Golden Dataset Model

Golden dataset is file-backed (`evals/golden/*.json`) and includes:

- `documents`: source fixtures for indexing
- `cases`: each case defines
  - `question`
  - `expected_document_keys`
  - `expected_chunk_indices`
  - `expected_abstain`
  - `citation_constraints`
  - `tags`, `difficulty`, `scenario_type`
  - optional retrieval controls (`top_k`, `score_threshold`)

## Eval Runner

`PgEvaluationRunner` executes end-to-end eval against PostgreSQL + pgvector backend.

Execution flow:

1. Load golden dataset from config.
2. Ensure dataset documents are ingested/indexed in PostgreSQL.
3. Upsert `eval_cases` with explicit expectation fields.
4. Execute per-case chat query through finite-state agent.
5. Compute and persist per-case `EvalResult` metrics.
6. Aggregate run summary and compute `gate_passed`.

## Metrics

### Retrieval

- `recall_at_k`
- `hit_rate_at_k`
- `mrr`

### Answer / Citation

- answer rate / abstain rate
- unsupported answer rate (answered without citations)
- citation presence / parseable / resolved rates
- citation integrity failure count

### Agent Regression

- step limit violations
- rewrite limit violations
- fallback visibility failures

## Gate Rules

Run fails when any of the following occurs:

- any case-level regression fails
- unsupported answer rate exceeds configured threshold
- any citation integrity failure exists
- any agent step/rewrite limit violation exists
- fallback used but not visible in trace steps

## Persistence

- `eval_runs`: run status + summary
- `eval_cases`: golden expectation schema
- `eval_results`: per-case score/pass/metrics/output/trace reference

## API

- `POST /evals/run`
- `GET /evals/{id}`
- `GET /evals/latest`

## Frontend

Eval dashboard shows:

- latest run summary
- key retrieval/answer/agent metrics
- failed case samples
- unsupported answer rate threshold highlight

## CI Gate

GitHub Actions gate enforces:

1. `make lint`
2. `make test`
3. `make eval`
4. `make smoke`

with PostgreSQL + pgvector service.
