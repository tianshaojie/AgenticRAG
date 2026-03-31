# Step 5 Observability, Resilience, and Health Hardening

## Structured Logging Fields

All logs are JSON with stable keys. Newly enforced fields include:

- `request_id`
- `trace_id`
- `query_id`
- `document_id`
- `agent_state`
- `latency_ms`
- `provider_name`
- `operation`
- `attempt`
- `fallback_used`
- `error_code`
- `error_category`

Request middleware logs request-level latency/status, while agent/provider calls emit operation-level logs.

## Timeout / Retry Strategy

Provider calls use bounded retry + timeout via `call_with_resilience`:

- timeout: `asyncio.wait_for`
- retry: exponential backoff
- retry cap: `max_retries + 1 attempts` (never unbounded)

Configurable per provider group:

- embedding: timeout + retries
- retrieval: timeout + retries
- rerank: timeout + retries
- generation: timeout + retries

Shared backoff settings:

- base backoff ms
- max backoff ms

## Error Model

Domain error categories:

- `validation`
- `dependency`
- `timeout`
- `internal`
- `unavailable`

Unified API error response schema:

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

Handled centrally for:

- app/domain exceptions
- request validation exceptions
- HTTP exceptions
- unexpected internal exceptions

## Fallback Paths

Implemented fallback behavior:

1. retrieval failure
- fallback path: `RETRIEVE -> ABSTAIN`
- reason: `retrieval_failure_fallback`

2. rerank failure
- fallback path: keep original retrieval candidates
- continue: `RERANK -> GENERATE_ANSWER`

3. generation failure
- fallback path: safe abstain with citations
- continue to terminal completion

All fallback events are trace-visible in `agent_trace_steps.output_payload`:

- `fallback=true`
- `fallback_stage`
- `fallback_reason`
- `error_code`

## Health / Readiness Model

`GET /health`

- liveness + dependency snapshot
- includes checks for db and pgvector capability

`GET /ready`

- readiness with strict dependency checks
- includes runtime summary counters from metrics abstraction

## PostgreSQL / pgvector Readiness Checks

Readiness checks include:

1. `database`
- query: `SELECT 1`

2. `pgvector_extension`
- query extension registry for `vector`

3. `pgvector_similarity`
- execute vector distance expression:
  - `SELECT '[1,0,0]'::vector <=> '[1,0,0]'::vector`

This ensures both extension presence and executable vector operations.

## Metrics Abstraction

Current abstraction tracks:

- request count
- error count
- latency observations (for p95)
- abstain count/ratio
- fallback count/ratio

Designed as replaceable in-memory recorder for later Prometheus/OTel integration.
