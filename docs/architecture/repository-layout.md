# Repository Layout

```text
backend/
  app/
    api/
    core/
    db/
    schemas/
    domain/
    ingestion/
    indexing/
    retrieval/
    services/
    agent/
    evals/
    observability/
  alembic/
  tests/

frontend/
  src/
    app/
    pages/
    components/
    features/
      chat/
      documents/
      traces/
      evals/
      settings/
    api/
    lib/
    types/
  tests/

docs/
  architecture/
  quality/

evals/
  demo_documents/
  golden/
  cases/
  reports/

scripts/
```

## Boundary Rules

- 后端路由层不直接耦合具体向量实现，依赖 `VectorIndex` 抽象
- retrieval 与 answer generation 必须可独立替换
- 前端通过 `src/api/contracts.ts` 与后端契约对齐
