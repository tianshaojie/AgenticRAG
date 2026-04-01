# Agentic RAG 工程建设指导（基于外部文档解读）

## 1. 目标定位

这份指导把《RAG一定要走向Agentic，什么是Agentic？它能解决什么问题？》中的观点，转换为本仓库可执行的工程架构与建设路线。  
文档强调 RAG 要从“线性管道”升级为“带反馈的决策系统”，核心能力是反思、规划、工具使用和自检。  
来源：PDF 第 1 页、第 2 页。

## 2. 关键结论（可直接作为建设原则）

1. Agentic 不是“多加几个 prompt”，而是把系统从一次性流程改造成可迭代决策流程。  
来源：PDF 第 1 页（Naive RAG 线性 vs Agentic 循环）。
2. 需要优先解决四类企业级问题：多跳拆解、检索质量纠错、多源路由、不知为不知。  
来源：PDF 第 1 页到第 2 页。
3. 核心工作流必须包含：查询分析、路由、迭代检索、重排过滤、反思评估。  
来源：PDF 第 2 页。
4. 最终目标是“高可用、高可靠”，而不是“一次生成看起来像对”。  
来源：PDF 第 2 页。

## 3. 架构落地（建议目标形态）

### 3.1 分层架构

1. `Query Analysis Layer`
   - 纠错、意图识别、关键词扩展。
2. `Routing Layer`
   - 按问题类型选择向量库 / SQL / API / 文档库。
3. `Retrieval Layer`
   - pgvector 召回 + metadata filter + top-k。
4. `Refinement Layer`
   - query rewrite（有限次数）+ rerank（可降级）。
5. `Evidence Gate Layer`
   - 证据充分性判断、冲突检测、abstain 判定。
6. `Generation Layer`
   - 严格基于证据生成，始终返回 citation。
7. `Critique & Trace Layer`
   - 结果忠实度检查、fallback 记录、全链路 trace 持久化。
8. `Eval & Regression Layer`
   - retrieval/answer/agent 回归门禁。

### 3.2 有限状态机（推荐升级版）

`INIT -> ANALYZE_QUERY -> ROUTE -> RETRIEVE -> EVALUATE_EVIDENCE -> (REWRITE_QUERY -> RETRIEVE)* -> RERANK -> GENERATE_ANSWER -> CRITIQUE -> COMPLETE | ABSTAIN | FAILED`

约束：
1. 必须有 `max_steps`。
2. 必须有 `max_rewrites`。
3. 任一步失败必须进入 `FAILED` 或显式 fallback，禁止静默吞错。

来源：PDF 第 1 页（循环与自纠）、第 2 页（核心工作流与评估）。

## 4. 痛点到能力的工程映射

1. 多跳问题拆解 -> `ANALYZE_QUERY + PLAN/ROUTE` + 子任务检索聚合。  
来源：PDF 第 1 页（Multi-hop Reasoning）。
2. 检索质量差 -> `EVALUATE_EVIDENCE + REWRITE_QUERY` 的闭环。  
来源：PDF 第 1 页（Self-Correction / Query Rewriting）。
3. 多数据源调度 -> 统一 `Tool Router`（向量检索、SQL、API）。  
来源：PDF 第 1 页（Tool Use / Routing）。
4. 不知为不知 -> `Evidence Gate + Critique`，证据不足强制 `ABSTAIN`。  
来源：PDF 第 2 页（Evaluation / 自检）。

## 5. 工程建设优先级（建议按阶段执行）

1. `P0: 可靠闭环`
   - 固化状态机上限、abstain-first、citation 完整性、trace 持久化。
2. `P1: 检索质量提升`
   - 引入 query rewrite 策略库、reranker 质量监控、metadata 路由优化。
3. `P2: 多工具路由`
   - 接入 SQL/API 工具并纳入统一 trace 与 fallback。
4. `P3: 自评估与回归门禁`
   - 将无证据作答率、citation 失真率、loop 超限率纳入 CI gate。

## 6. 验收指标（建议作为发布门禁）

1. `citation_integrity_pass_rate = 100%`
2. `unsupported_answer_rate <= 阈值`
3. `abstain_precision` 持续可观测
4. `agent_step_overflow = 0`
5. `fallback_path_observable = 100%`

来源：PDF 第 2 页（反思评估与可靠性目标）。

## 7. 当前项目的直接行动建议

1. 在现有 `agent policy` 中补充 `ROUTE` 与 `CRITIQUE` 为一等状态。
2. 将 provider check 与运行时配置纳入 trace（便于“为何失败”定位）。
3. 为多源检索预留统一 `ToolResult` 契约，避免后续隐式耦合。
4. 把“证据冲突”从 reason 升级为结构化字段（冲突类型、冲突片段集合）。

## 8. 来源说明

- 原始文档：`/Users/tianshaojie/Downloads/RAG一定要走向Agentic，什么是Agentic？它能解决什么问题？.pdf`
- 主要引用页：
  - 第 1 页：Agentic 定义、四类痛点、核心公式。
  - 第 2 页：核心工作流、评估与总结。

## 9. 旧 Sprint1 复用与舍弃（重规划基线）

### 9.1 保留（继续演进）

1. 有限状态机主干（含 `max_steps` / `max_rewrites`）。
2. `agent_traces` / `agent_trace_steps` 持久化与 step 级 fallback 记录。
3. `ABSTAIN` 优先的安全策略与 citation 完整性约束。
4. retrieval/rerank/generation 的 resilience 包装（timeout/retry/fallback）。

### 9.2 舍弃或重写

1. 过于简化的 query analysis（仅长度判断）改为结构化分析输出。
2. 过于简化的 route 规则（仅前缀判断）改为显式 router 决策对象。
3. trace 中缺失 query analysis/routing 细粒度字段的问题在新 Sprint1 修复。

## 10. 新 Sprint1（能力导向）范围

目标：只聚焦两项 Agentic 核心能力的工程化落地。

1. `Query Analysis`
   - 输出：`normalized_query` / `corrected_query` / `expanded_terms` / `intent` /
     `need_retrieval` / `confidence` / `reasons`。
2. `Routing`
   - 输出：`preferred_route` / `selected_route` / `reason` / `fallback` / `confidence`。
3. trace 必须可读到上述结构化输入输出。
4. 单测与集成测试覆盖这两项能力。

## 11. 新 Sprint2（能力导向）范围

目标：聚焦迭代检索质量控制与重排过滤分层。

1. `Iterative Retrieval`
   - 在检索步记录 `top_score`、`score_gain`、`stagnation_count`。
   - 当多轮 rewrite 后检索质量不提升时，触发保守 `ABSTAIN`（`retrieval_stagnated`）。
2. `Re-ranking & Filtering`
   - 固化分层链路：`retrieve -> optional rerank -> evidence filter`。
   - filter 规则：去重、最小分数、每文档 chunk 上限。
   - filter 后为空时直接 `ABSTAIN`（`filtered_evidence_empty`）。
3. 验收
   - 新增 `EvidenceFilter` 单测。
   - 新增 executor 集成测试覆盖停滞停止与 filter 为空拒答。

## 12. 新 Sprint3（能力导向）范围

目标：聚焦 `Critique` 与 `Agentic E2E 回归门禁`。

1. `Critique（反思评估）`
   - 将冲突信号升级为结构化字段：`conflict_type` / `conflict_chunk_ids` / `conflict_score_gap`。
   - 在 `CRITIQUE` 步强制不确定性标注：冲突场景回答必须显式包含 uncertainty 信号。
   - 在 trace run-level meta 中落库冲突摘要，便于回溯。
2. `Agentic E2E Regression Gate`
   - 在 eval runner 增加按 case tags 的能力检查（query analysis / routing / iterative retrieval / rerank-filter / conflict critique）。
   - `golden_v1` 升级为覆盖 5 个核心动作的数据集。
   - 任一 agentic 能力检查失败，视为 gate fail。
3. 验收
   - 新增冲突结构化输出测试。
   - 新增 conflict regression gate 测试（预期失败样例必须拦截）。

## 13. 新 Sprint4（能力导向）范围

目标：聚焦 `多源 Routing` 的真实工具接入（P2）。

1. `Routing -> Tool Retriever`
   - 将 `ROUTE` 结果接入可插拔检索器映射：`pgvector/sql/api`。
   - 在 trace 中记录 `route_retriever`，保障“选了哪条路、由谁执行”可回溯。
2. `Fallback`
   - 选中的 route retriever 缺失时，保守降级到 `pgvector` 并显式记录 `route_reason`。
   - 若无可用 retriever，则 `ABSTAIN`，禁止静默失败。
3. `SQL/API 最小实现`
   - `sql`：词法检索器（去 SQL 停用词、按命中率打分）。
   - `api`：词法检索器（去 API 噪音词、按命中率打分）。
   - 证据身份保持 chunk/doc/span 一致，不改 citation 身份。
4. 验收
   - executor 集成测试覆盖：`sql/api` 路由命中、retriever 缺失回退。
   - route retriever 独立测试覆盖：前缀解析、得分和 metadata 标记。

## 14. 核心动作覆盖矩阵（补全）

为避免“只做到 Sprint4 就停止”的误解，下面明确 5 个核心动作与阶段覆盖关系：

1. `Query Analysis` -> Sprint1（结构化输出 + trace）
2. `Routing` -> Sprint1/Sprint4（路由决策 + 多源 retriever 映射）
3. `Iterative Retrieval` -> Sprint2（rewrite 循环、停滞停止、上限控制）
4. `Re-ranking & Filtering` -> Sprint2（分层链路 + rerank 失败回退）
5. `Critique` -> Sprint3（冲突结构化 + uncertainty 标注 + 决策约束）
6. `Agentic E2E Regression Gate` -> Sprint3（golden + gate）

结论：核心动作在 Sprint1~Sprint4 已全部覆盖到“功能形态”，但还缺少“可替换工具执行层”的工程硬化，因此新增 Sprint5。

## 15. 新 Sprint5（能力导向）范围

目标：在不改动核心策略语义前提下，补齐 `Routing / Retrieval` 执行层的可替换性、可降级性和可测试性，作为进入生产化迭代的基线。

1. `Route Provider 抽象化`
   - 为 `sql/api` 路由检索定义统一 provider 接口与输入输出契约。
   - Route retriever 仅依赖接口，不直接耦合具体实现细节。
2. `Provider Factory + 配置注入`
   - 支持按配置切换 `local lexical provider / mock provider`。
   - executor 通过工厂装配 route retriever，避免硬编码实例。
3. `失败降级与可观测`
   - route provider 不可用或执行失败时，保守降级到 `pgvector`；若不可降级则 `ABSTAIN`。
   - trace 必须记录 `route_retriever`、`route_provider`、`route_reason`、`fallback`。
4. `测试与门禁`
   - 新增 provider 单测（契约、映射、fallback）。
   - 新增 executor 集成测试（provider 切换、失败降级路径）。
   - 保持 `test/eval/smoke` 全绿作为 Sprint5 完成条件。
