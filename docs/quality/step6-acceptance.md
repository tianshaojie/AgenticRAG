# Step 6 Acceptance

## Required Commands

- `make lint`
- `make test`
- `make eval`
- `make smoke`

All commands must pass to satisfy CI gate.

## Eval Quality Gate

A run is gate-passed only when:

- `failed_cases == 0`
- `unsupported_answer_rate <= RAG_EVAL_MAX_UNSUPPORTED_ANSWER_RATE`
- `citation_integrity_failures == 0`
- `agent.step_limit_violations == 0`
- `agent.rewrite_limit_violations == 0`
- `agent.fallback_visibility_failures == 0`

## Regression Requirements

Per-case metrics must include:

- retrieval metrics (`recall_at_k`, `hit_rate_at_k`, `mrr`)
- answer behavior (`answered`, `unsupported_answer`, `citation_count`)
- citation integrity (`present`, `parseable`, `resolved`, mismatch reasons)
- agent controls (`step_count`, `rewrite_count`, `fallback visibility`)

## CI Failure Conditions

CI fails when:

- lint/test/smoke fails
- eval gate fails
- citation integrity check fails in any case
- agent loop/rewrite limits are exceeded

## Frontend Dashboard Baseline

Eval page must show:

- latest run status and gate result
- key retrieval/answer/agent metrics
- failed case list with reasons
- unsupported answer rate warning highlight
