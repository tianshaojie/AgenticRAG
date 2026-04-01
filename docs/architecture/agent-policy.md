# Agent Policy (Finite State)

## Design Goal

Agent execution must be bounded, debuggable, and auditable.

## States

1. `INIT`
2. `ANALYZE_QUERY`
3. `ROUTE`
4. `RETRIEVE`
5. `EVALUATE_EVIDENCE`
6. `REWRITE_QUERY`
7. `RERANK`
8. `GENERATE_ANSWER`
9. `CRITIQUE`
10. `ABSTAIN`
11. `COMPLETE`
12. `FAILED`

`COMPLETE`, `ABSTAIN`, and `FAILED` are terminal states.

## Stop Conditions

1. Terminal state reached.
2. `agent_max_steps` reached.
3. `agent_max_rewrites` reached.
4. Retrieval stagnation reached (`agent_retrieval_stagnation_limit` with low score gain).

No open-ended loop is allowed.

## Fallback Rules

1. Retrieval failure -> fallback path recorded in trace, then abstain or degraded completion.
2. Rerank failure -> use retrieval candidates directly, fallback marked.
3. Generation failure -> abstain with fallback metadata.
4. Route target unavailable -> fallback to `pgvector` and record `route_reason`.
5. Critique detects unsupported answer -> force `ABSTAIN` with explicit reason.

Any fallback must be visible in `agent_trace_steps.output_payload`.

## Evidence Policy

1. Citation count and score thresholds are mandatory.
2. Insufficient evidence -> `ABSTAIN`.
3. Conflict evidence -> return uncertainty signal in answer metadata/reason.
   - Structured conflict fields: `conflict_type`, `conflict_chunk_ids`, `conflict_score_gap`.
4. Reranked evidence must pass filtering (`min_score`, per-document cap, dedupe).
5. Filtered evidence empty -> `ABSTAIN` with `filtered_evidence_empty`.

## Iterative Retrieval Guard

1. Each `RETRIEVE` step records:
   - `top_score`
   - `previous_top_score`
   - `score_gain`
   - `stagnation_count`
2. If score gain does not improve beyond `agent_retrieval_min_score_gain` for
   `agent_retrieval_stagnation_limit` iterations, policy forces abstain.
3. This prevents rewrite loops that keep searching without evidence quality improvement.

## Query Analysis and Routing Contract

1. `ANALYZE_QUERY` writes structured fields into trace payload:
   - `normalized_query`
   - `corrected_query`
   - `expanded_terms`
   - `intent`
   - `need_retrieval`
   - `confidence`
   - `reasons`
2. `ROUTE` writes:
   - `preferred_route`
   - `selected_route`
   - `available_routes`
   - `route_reason`
   - `route_confidence`
   - `route_retriever`
   - `fallback`
3. Retrieval supports layered route retrievers:
   - `pgvector` (vector-first with lexical fallback)
   - `sql` (lexical SQL-intent retriever)
   - `api` (lexical API-intent retriever)
4. If a selected route retriever is unavailable at runtime, policy falls back to `pgvector` with
   explicit `route_reason` and `fallback=true`. If no route retriever exists, policy abstains.

## Trace Persistence

1. `agent_traces` stores run-level metadata (`request_id`, `trace_id`, start/end states).
2. `agent_trace_steps` stores per-step state/action/status/latency/fallback/error.

The trace model is required for production debugging and regression checks.
