# Release Acceptance (Pre-Production)

## Mandatory Gates

1. `make lint`
2. `make test`
3. `make smoke`
4. `make eval`
5. `make build`

All commands must pass before handoff.

## Functional Expectations

1. Documents can be uploaded, listed, indexed, and retried on failure.
2. Chat answers must include citation fields in response schema.
3. No-evidence path must abstain.
4. Trace endpoint must return persisted step timeline.
5. Eval endpoint must return deterministic summary and failed case detail.
6. Health/readiness must include PostgreSQL + pgvector checks.

## Reliability Expectations

1. Agent loop is bounded by configured max steps and max rewrites.
2. Provider-like calls are timeout and retry bounded.
3. Fallback behavior is visible in traces.
4. Error responses follow stable schema.

## Non-Goals for Current Release

1. Real external LLM provider optimization.
2. Streaming token response.
3. Large-scale ANN tuning at >10M vectors.
4. Multi-tenant RBAC and audit policy.
