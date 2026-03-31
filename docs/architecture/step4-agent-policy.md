# Step 4 Finite-State Agent Policy

## State Machine

Implemented state set:

- `INIT`
- `ANALYZE_QUERY`
- `RETRIEVE`
- `EVALUATE_EVIDENCE`
- `REWRITE_QUERY`
- `RERANK`
- `GENERATE_ANSWER`
- `ABSTAIN`
- `COMPLETE`
- `FAILED`

Primary transition flow:

1. `INIT -> ANALYZE_QUERY`
2. `ANALYZE_QUERY -> RETRIEVE | ABSTAIN`
3. `RETRIEVE -> EVALUATE_EVIDENCE | FAILED`
4. `EVALUATE_EVIDENCE -> RERANK | REWRITE_QUERY | ABSTAIN`
5. `REWRITE_QUERY -> RETRIEVE | FAILED`
6. `RERANK -> GENERATE_ANSWER | FAILED`
7. `GENERATE_ANSWER -> COMPLETE | FAILED`

Terminal states:

- `ABSTAIN`
- `COMPLETE`
- `FAILED`

## Stop Conditions

Execution stops when any of the following is true:

- terminal state reached
- `agent_max_steps` reached (forced `FAILED`, reason `max_steps_exceeded`)
- evidence judged insufficient and rewrite budget exhausted
- unrecoverable exception in any step (`FAILED` path)

Budget controls:

- `agent_max_steps`
- `agent_max_rewrites`

## Evidence & Decision Strategy

- `DefaultEvidenceSufficiencyJudge` decides:
  - sufficiency (`min_results`, `min_score`)
  - conflict (`conflict_delta` + opposite negation signals)
- insufficient evidence triggers rewrite if budget remains
- if rewrite budget exhausted, transition to `ABSTAIN`
- conflict is surfaced as explicit uncertainty text in final answer

## Rerank Layer

- `BasicReranker` runs after evidence is sufficient
- current strategy: lexical overlap + retrieval score weighted mix
- rerank is second stage only (after pgvector retrieval)

## Trace Persistence (PostgreSQL)

- Trace root: `agent_traces`
  - session binding
  - start/end state
  - status (`running/success/abstained/failed`)
  - request metadata (`request_id`, `trace_id`)
  - execution metadata (`rewrite_count`, `fallback_used`, `abstain_reason`)
- Step details: `agent_trace_steps`
  - strict step order (`trace_id`, `step_order` unique)
  - state/action/status
  - input/output payload (contains summary fields)
  - per-step latency and error message

Each step records:

- input summary
- output summary
- status transition target (`next_state` in output payload)
- latency ms
- fallback marker
- error detail (if failed)

## API Surface (Step 4)

- `POST /chat/query` now executes finite-state agent policy
- `GET /chat/{id}/trace` returns latest trace for session `{id}`

## Current Boundaries

- deterministic local embedder and deterministic rewrite
- no complex planning / tool-use loop
- no multi-hop decomposition
- no provider-specific LLM optimization
- no async job queue (request-scope execution)

