# Eval Methodology

## Purpose

Provide repeatable quality gates for retrieval, answer grounding, citation integrity, and agent behavior.

## Dataset Model

Golden dataset is JSON file based and contains:

1. `documents`
2. `cases`
3. Case expectations:
- `question`
- `expected_document_keys`
- `expected_chunk_indices`
- `expected_abstain`
- `citation_constraints`
- `tags`, `difficulty`, `scenario_type`

## Execution Flow

1. Load dataset.
2. Ensure dataset documents are ingested and indexed.
3. Upsert `eval_cases`.
4. Execute case queries through the same chat/agent path as runtime.
5. Persist `eval_results`.
6. Aggregate `eval_runs.summary`.
7. Apply gate policy.

## Metrics

1. Retrieval:
- `recall_at_k`
- `hit_rate_at_k`
- `mrr`

2. Answer/Citation:
- `answer_rate`
- `abstain_rate`
- `unsupported_answer_rate`
- `citation_presence_rate`
- `citation_parseable_rate`
- `citation_resolved_rate`
- `citation_integrity_failures`

3. Agent regression:
- `step_limit_violations`
- `rewrite_limit_violations`
- `fallback_visibility_failures`
- `agentic_capability_failures` (tag-driven checks)

4. Agentic capability checks (tag-driven):
- `query_analysis`: analysis step payload completeness
- `routing`: route decision payload completeness
- `route_fallback`: fallback visibility in route step
- `iterative_retrieval`: retrieval step stagnation metrics visibility
- `rerank_filter`: rerank/filter payload completeness
- `conflict`: uncertainty signal + conflict reason consistency

## Gate Failure Conditions

Run fails when any condition is true:

1. Any case fails.
2. Unsupported answer rate exceeds configured threshold.
3. Citation integrity failures > 0.
4. Agent step/rewrite limit violations > 0.
5. Fallback visibility failures > 0.
6. Any `agentic_*` capability regression detected.

## Storage

1. `eval_runs`: run status + summary.
2. `eval_cases`: normalized expected behavior.
3. `eval_results`: per-case outputs and metrics.

## Commands

```bash
make eval
python -m app.evals.cli --dataset golden_v1 --name local-eval
python -m app.evals.cli --dataset golden_minimal --name smoke-eval
```
