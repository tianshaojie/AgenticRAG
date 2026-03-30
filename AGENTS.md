# AGENTS.md

## Scope Guardrails (Current Phase Only)

This repository is currently in **Step 1**: architecture, scaffolding, schema design, and API boundaries.

### Allowed in this phase
- Repository structure and module skeletons
- Architecture and quality documentation
- Database schema design and migration skeleton
- Interface contracts and route placeholders
- Test/eval directory setup with smoke-level checks

### Not allowed in this phase
- Full business logic implementation
- Real LLM provider integration
- Complex prompts or open-ended autonomous loops
- UI polish work
- Skipping schema design

## Engineering Principles
- Verifiability over cleverness
- Explicit module boundaries over implicit coupling
- Conservative abstain/fallback over unsupported claims
- Testable and evaluable workflows over one-off features
- Agent flow must be finite-state (no unbounded loop)
- External calls must use timeout, retry, and structured logging

## Evidence Policy
- Assistant answers must include citations to retrieved evidence
- If evidence is insufficient, return abstain/fallback

## Storage Policy
- Business data: PostgreSQL
- Vector index: PostgreSQL + pgvector
- No external vector DB dependency for current implementation

## Observability
- Structured logging required
- Every request carries trace-friendly metadata (`request_id`, `trace_id`)

## Definition of Done (Phase)
- Schema and migration skeleton complete
- Required interfaces declared
- Required routes exposed with typed contracts
- Frontend pages and API client skeletons present
- Baseline tests and eval folder scaffolding present
