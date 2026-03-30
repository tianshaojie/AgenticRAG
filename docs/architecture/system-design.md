# Agentic RAG System Design (Step 1)

## 1. 目标与范围

本阶段目标是构建**可演进、可测试、可迁移**的生产级骨架，不实现完整业务。

- 完成目录与模块边界
- 完成 PostgreSQL + pgvector schema 设计
- 完成 API contract 骨架（FastAPI + OpenAPI）
- 完成前端页面与 API client 骨架
- 完成 Alembic 初始化迁移骨架
- 完成基础可验证测试

## 2. 非目标（本阶段禁止）

- 真实 LLM provider 接入
- 复杂 prompt 或自动循环 Agent
- 复杂检索/重排业务逻辑
- UI 精细化打磨

## 3. 模块边界

### Backend (`backend/app`)

- `api/`: FastAPI 路由与依赖
- `core/`: 配置与常量
- `db/`: SQLAlchemy model/session
- `schemas/`: Pydantic 请求响应契约
- `domain/`: 领域枚举与核心接口协议
- `ingestion/`: 文档导入接口层
- `indexing/`: 向量索引抽象与 pgvector 默认实现
- `retrieval/`: 检索/重排流程骨架
- `services/`: 可替换服务 stub
- `agent/`: 有限状态机
- `evals/`: 评估执行接口
- `observability/`: 结构化日志与请求元数据中间件

### Frontend (`frontend/src`)

- `pages/`: 页面骨架（Documents/Chat/Traces/Evals/Settings）
- `components/`: 共享组件（含 Citation Panel）
- `features/`: 按域拆分的后续实现入口
- `api/`: 与后端一一对应的 typed contract + client
- `lib/`: 基础 HTTP 客户端（默认 timeout）

## 4. Agent 有限状态设计

状态集（终态不可再转移）：

- `RECEIVED` -> `RETRIEVING`
- `RETRIEVING` -> `RERANKING | ABSTAIN | FAILED`
- `RERANKING` -> `SYNTHESIZING | ABSTAIN | FAILED`
- `SYNTHESIZING` -> `CITING | ABSTAIN | FAILED`
- `CITING` -> `COMPLETE | ABSTAIN | FAILED`
- `COMPLETE | ABSTAIN | FAILED` 为终态

该设计显式禁止开放式无限循环。

## 5. PostgreSQL 领域模型

核心表：

- `documents`
- `document_versions`
- `document_chunks`
- `chunk_vectors`
- `chat_sessions`
- `chat_messages`
- `agent_traces`
- `agent_trace_steps`
- `eval_cases`
- `eval_runs`
- `eval_results`

设计要点：

- 所有主键均为 UUID
- 时间字段统一 `timestamptz`
- 扩展字段使用 `jsonb metadata`（model 中以 `meta` 映射）
- 对 trace、message、eval 建立查询索引
- 使用显式版本表 `document_versions` 支持重索引与审计

## 6. pgvector 设计

### 6.1 向量列位置

向量列放在 `chunk_vectors.embedding`，与文本 chunk 解耦：

- `document_chunks` 负责文本与位置
- `chunk_vectors` 负责 embedding 与 embedding model
- 同一 chunk 可挂多个 embedding model（`unique(chunk_id, embedding_model)`）

### 6.2 默认距离策略

默认采用 **cosine distance**：

- 索引：`ivfflat (embedding vector_cosine_ops)`
- 查询排序：`embedding <=> :query_vector`（越小越近）

### 6.3 Top-k Retrieval SQL（设计示例）

```sql
SELECT
  cv.chunk_id,
  dc.document_id,
  dc.content,
  (cv.embedding <=> :query_vector) AS distance
FROM chunk_vectors cv
JOIN document_chunks dc ON dc.id = cv.chunk_id
WHERE cv.embedding_model = :embedding_model
  AND dc.metadata @> :metadata_filter::jsonb
ORDER BY cv.embedding <=> :query_vector
LIMIT :top_k;
```

### 6.4 Metadata Filter 扩展策略

- 当前：`jsonb @>` + GIN 索引（灵活）
- 后续：对高选择性字段上提为显式列（如 `tenant_id`, `document_type`, `language`）
- 多租户隔离优先使用强约束列过滤，再叠加 jsonb 过滤

### 6.5 与 Rerank 的分层协作

- Stage-1：pgvector 召回 `top_k`
- Stage-2：Reranker 将 `top_k -> top_n`
- Stage-3：CitationAssembler 从 `top_n` 产出引用
- Stage-4：AnswerGenerator 基于 citation 生成答案；无证据则 abstain

## 7. 可观测性

- 中间件注入 `X-Request-ID` / `X-Trace-ID`
- 结构化 JSON 日志包含：`request_id`, `trace_id`, `path`, `method`, `status_code`
- agent trace 结构化落库由 `agent_traces` + `agent_trace_steps` 承接

## 8. 外部调用约束

当前未接入外部 provider，但配置层已预留：

- `RAG_REQUEST_TIMEOUT_SECONDS`
- `RAG_REQUEST_RETRY_ATTEMPTS`

后续所有外部调用必须统一接入 timeout/retry/logging wrapper。

## 9. 假设与保守决策

- 默认 embedding 维度先固定为 1536（后续可迁移扩展）
- `/ready` 本阶段返回 `degraded`（不做真实依赖探测）
- `/chat/query` 本阶段默认 abstain（无证据不猜测）
