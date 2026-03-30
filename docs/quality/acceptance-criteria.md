# Quality Acceptance Criteria (Step 1)

## 1. 结构与边界

- [x] 目录结构符合阶段要求
- [x] 必需模块已创建
- [x] 核心接口协议已定义（10 个）
- [x] Agent 为有限状态流程

## 2. 数据与迁移

- [x] PostgreSQL 业务表设计完整
- [x] pgvector 表与索引策略明确
- [x] Alembic 初始迁移骨架可用
- [x] 文档/chunk/embedding/trace 元数据 schema 明确

## 3. API 与契约

- [x] 指定 9 个路由已定义
- [x] Pydantic 请求响应模型已建立
- [x] OpenAPI 可由 FastAPI 自动生成

## 4. 前端骨架

- [x] 指定页面骨架已创建
- [x] API client 与 contract 类型已创建
- [x] features 目录按域拆分

## 5. 验证与测试

- [x] backend tests 目录已创建
- [x] frontend tests 目录已创建
- [x] evals 目录骨架已创建
- [x] 至少存在 smoke 级测试

## 6. 观测与可靠性约束

- [x] 结构化日志能力已接入
- [x] request_id/trace_id 中间件已接入
- [x] 配置层已预留 timeout/retry 参数

## Exit Criteria

Step 1 结束前必须满足：

1. 目录、文档、schema、路由、迁移、测试骨架全部存在。
2. 不包含真实 provider 接入与复杂 agent loop。
3. 默认行为遵循保守 abstain。
