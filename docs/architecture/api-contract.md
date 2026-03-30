# API Contract Skeleton (Step 1)

基于 FastAPI OpenAPI 自动生成。当前仅定义契约与占位返回。

## Routes

1. `POST /documents`
2. `GET /documents`
3. `POST /documents/{id}/index`
4. `POST /chat/query`
5. `GET /chat/{id}/trace`
6. `GET /health`
7. `GET /ready`
8. `POST /evals/run`
9. `GET /evals/{id}`

## Contract Notes

- `POST /chat/query` 当前默认返回 `abstained=true`
- citation 结构已固定：`chunk_id/document_id/quote/score`
- trace endpoint 返回有限状态步骤骨架
- eval endpoint 返回 run 受理与读取骨架

## OpenAPI 生成

后端启动后访问：

- `/openapi.json`
- `/docs`

可用于前端类型同步与契约测试。
