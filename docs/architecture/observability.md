# Observability

## Logging

Structured logs are emitted with correlation fields:

1. `request_id`
2. `trace_id`
3. `document_id` or `query_id` when available
4. `agent_state`
5. `latency_ms`
6. `provider_name`
7. `fallback_used`

## Request Metadata

Middleware injects stable request metadata from headers (or generates defaults):

1. `X-Request-ID`
2. `X-Trace-ID`

These IDs are propagated into trace rows and error responses.

## Error Modeling

Stable API error schema:

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

## Timeout / Retry

Provider-like operations (embedding/retrieval/rerank/generation) use bounded timeout and retry policy from settings:

1. `<stage>_timeout_seconds`
2. `<stage>_retry_attempts`
3. bounded exponential backoff controls

No unbounded retry is allowed.

## Health and Readiness

1. `GET /health` returns service + dependency checks.
2. `GET /ready` returns dependency checks + runtime summary.

Dependency checks include:

1. PostgreSQL connectivity
2. pgvector extension presence
3. pgvector similarity query sanity check

## Metrics Abstraction

Current in-process metrics expose counters/ratios for:

1. request count
2. error count
3. latency distribution hooks
4. abstain ratio
5. fallback ratio

This abstraction is ready for Prometheus/OpenTelemetry exporter integration.
