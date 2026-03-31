# Agent Policy (Finite State)

## Design Goal

Agent execution must be bounded, debuggable, and auditable.

## States

1. `INIT`
2. `ANALYZE_QUERY`
3. `RETRIEVE`
4. `EVALUATE_EVIDENCE`
5. `REWRITE_QUERY`
6. `RERANK`
7. `GENERATE_ANSWER`
8. `ABSTAIN`
9. `COMPLETE`
10. `FAILED`

`COMPLETE`, `ABSTAIN`, and `FAILED` are terminal states.

## Stop Conditions

1. Terminal state reached.
2. `agent_max_steps` reached.
3. `agent_max_rewrites` reached.

No open-ended loop is allowed.

## Fallback Rules

1. Retrieval failure -> fallback path recorded in trace, then abstain or degraded completion.
2. Rerank failure -> use retrieval candidates directly, fallback marked.
3. Generation failure -> abstain with fallback metadata.

Any fallback must be visible in `agent_trace_steps.output_payload`.

## Evidence Policy

1. Citation count and score thresholds are mandatory.
2. Insufficient evidence -> `ABSTAIN`.
3. Conflict evidence -> return uncertainty signal in answer metadata/reason.

## Trace Persistence

1. `agent_traces` stores run-level metadata (`request_id`, `trace_id`, start/end states).
2. `agent_trace_steps` stores per-step state/action/status/latency/fallback/error.

The trace model is required for production debugging and regression checks.
