# Agent 落地进展：已实践与待开发

> 日期：2026-11-05  
> 代码位置：`agent_service/`  
> 运行方式：LangGraph Phase-0 参考实现，本地已验证  
> 说明：本轮没有修改现有 Java 电商业务代码；新增的是独立 Agent 服务与评测脚本。

---

## 1. 结论

已从“规划”推进到**可运行的 Phase-0 参考实现**：

- LangGraph 图编排；
- Supervisor + 5 个子 Agent；
- 商品/订单/售后/FAQ 工具；
- 每次 LLM 调用和工具调用的 trace；
- 8 条 golden cases 的离线评测；
- 单元测试与本地电商接口联调。

已完成真实 LLM（DeepSeek `deepseek-flash`）链路验证、pgvector RAG 与 trace PostgreSQL 持久化；尚未完成生产级 Java 落地、写操作、会话持久化/SFT。

---

## 2. 已实践

### 2.1 Agent 编排

| 项 | 实现 |
|---|---|
| 图编排 | `app/graph.py`，LangGraph `StateGraph` |
| 节点 | `route → shopping/order_status/after_sale/knowledge/handoff → finalize` |
| 主 Agent | `route` 节点做意图路由 |
| 子 Agent | `app/agents.py` 中 5 个 Agent |
| 工具层 | `app/tools.py`，通过 REST 调 commerce，不直读数据库 |
| 知识库 | `app/rag.py`，FAQ 入 pgvector，语义检索；失败降级关键词 |
| 状态 | `AgentState`：消息、会话、意图、Agent、工具结果、trace |
| 会话 | `SessionStore` 保留最近 6 轮（内存，Phase-0） |

### 2.2 LLM 网关

- `RuleBasedLlmGateway`：无 API Key 时用于本地验证编排和 trace；
- `OpenAiCompatibleLlmGateway`：已实现 OpenAI-compatible `/chat/completions` 调用；
- 通过 `AGENT_LLM_BASE_URL/AGENT_LLM_MODEL/AGENT_LLM_API_KEY_FILE` 自动切换；
- 支持从文件读取 API Key，避免把密钥写进代码或对话；
- 已用 DeepSeek `deepseek-flash` 完成真实调用验证。

### 2.3 监控

每次 run 记录：

- `run_id/trace_id/session_id/customer_id`；
- `intent/agent/status/latency`；
- 每次 LLM：prompt、response、model、token、latency；
- 每次工具：name、args、result、status、latency；
- 每次检索：backend、query、hits、score、fallback；
- LangGraph 节点回调事件；
- trace 查询 API + metrics API；
- 默认 JSONL：`agent_service/artifacts/agent-traces.jsonl`；
- `AGENT_TRACE_BACKEND=postgres`：run 元数据 + 完整 trace JSONB 落 PostgreSQL，重启后仍可按 `run_id` 查询；
- 存储故障自动降级 JSONL，并在 `health.trace_error` 暴露原因。

脱敏：trace 会把 `authorization/token/password` 替换为 `***`，手机号/邮箱做掩码。

### 2.4 评测

已实现：

- `eval/cases.jsonl`：8 条 golden cases；
- `eval/run_eval.py`：确定性指标；
- 指标：意图、子 Agent、状态、工具、答案事实、trace 覆盖率、平均延迟；
- 报告：`eval/report.json`。

### 2.5 可视化评测面板

- `GET /eval`：本地只读页面，无需前端构建；
- 切换规则模型 / DeepSeek 报告；
- 展示指标卡、逐条用例答案、期望 vs 实际、工具调用；
- 用例详情内展示完整 trace 时间线（LLM、工具、检索）；
- “运行记录”页读取 `/agent/runs`，支持查看 PostgreSQL/JSONL 中的 run。

### 2.6 安全边界

- 写操作没有真正执行：售后 Agent 只到 `need_confirmation`；
- 订单查询必须带登录 token；
- trace 不保存 token；
- 无 token 查订单返回 `need_auth`。

---

## 3. 验证结果

### 3.1 单元测试

```text
.venv/bin/python -m pytest -q
6 passed in 0.29s
```

覆盖：

- 购物路由 + 工具 + trace；
- 无 token 查订单 -> `need_auth`；
- 有 token 查订单 -> `getOrders`，trace 不含 token；
- 售后 -> `need_confirmation`，确认前不调用写工具；
- 投诉 -> `handoff`。

### 3.2 离线评测

```text
.venv/bin/python eval/run_eval.py
```

结果：

```json
{
  "total": 8,
  "intent_accuracy": 1.0,
  "agent_accuracy": 1.0,
  "status_accuracy": 1.0,
  "tool_accuracy": 1.0,
  "answer_fact_accuracy": 1.0,
  "trace_coverage": 1.0,
  "avg_latency_ms": 2.3,
  "case_pass_rate": 1.0
}
```

### 3.3 真实 LLM 调用链路（DeepSeek）

模型：`deepseek-flash`（DeepSeek 当前 flash 实际模型 id；`v4.1flash` 不是可调用的模型 id）。

购物场景实测：

```text
POST /agent/chat {"message":"帮我找一顶露营帐篷"}
-> HTTP 200, 2.92s, ShoppingGuideAgent
-> answer: 双人帐篷 防雨款 ¥599–619
-> trace: 2 次 LLM 调用（route + ShoppingGuideAgent）
   route: deepseek-flash, input 71 / output 44 tokens, 1173ms
   answer: deepseek-flash, input 107 / output 72 tokens, 1617ms
   tool: searchProducts 118ms
```

订单场景实测（真实登录 token）：

```text
POST /agent/chat {"message":"我的订单到哪了？"}
-> HTTP 200, 3.50s, OrderAgent
-> 5 笔 PENDING_SHIP 订单
-> trace: 2 次 LLM 调用 + getOrders 35.9ms
-> trace 中未出现 JWT / Bearer token
```

真实模型评测：

```text
8/8 cases passed（连续两轮）
intent_accuracy=1.0
agent_accuracy=1.0
status_accuracy=1.0
tool_accuracy=1.0
answer_fact_accuracy=1.0
trace_coverage=1.0
avg_latency_ms=2172.819 / 2504.751
report: agent_service/eval/report-real.json
```

评测过程中发现并修复了两个稳定性问题：

- 「支持开票吗？」曾被路由为 `shopping`：在路由 prompt 中加入判定优先级和 5 条 few-shot，复测稳定为 `knowledge`；
- 「电子普票」不包含精确字符串「发票」：评测新增 `answer_any`，支持同义表达任一命中。

### 3.4 pgvector RAG

已把 `data/faq.json` 入本地 `shang-postgres`（pgvector 0.8.6）：

```text
BAAI/bge-small-zh-v1.5, 512 维
CREATE TABLE agent_knowledge_chunk (... embedding vector(512) ...)
HNSW cosine index
```

检索自检：

```text
查询：退款一般多久到账？
0.8182  退款到账    退款审核通过后原路退回，通常 1-3 个工作日到账。
0.5958  退货政策    签收后 7 天内可申请无理由退货...
0.5555  物流时效    现货商品一般 48 小时内发货...
```

真实模型知识问答：

```text
POST /agent/chat "退款一般多久到账？"
-> KnowledgeAgent, 3.45s
-> searchFaq 54.7ms, backend=pgvector
-> trace.retrievals[0].hits[0] = 退款到账, score=0.8182
```

降级：数据库/embedding 不可用时自动回退关键词检索，并在 `retrievals[].fallback=true` 和 `error` 中记录原因。

### 3.5 trace 持久化

表：`agent_run_trace`，字段包含 `run_id/trace_id/session_id/status/agent/intent/latency_ms/started_at/finished_at` 和完整 `payload JSONB`。

实测：

```text
GET /health -> trace_store=postgres, trace_error=null
POST /agent/chat "退货政策是什么？" -> run_3a53ca67f34e485a82cb24b4d9730959
DB: 1 row, retrievals=1
重启服务
GET /agent/runs/run_3a53... -> 仍返回同一 trace
GET /agent/runs -> 1 条（从 DB 读取）
```

### 3.6 可视化面板验证

```text
GET /eval -> 200, 24.7KB HTML
GET /eval/reports -> rule/deepseek 两份报告，各 8 条
GET /eval/reports/real -> deepseek-flash, metrics 全 1.0, trace=true
Chrome headless 1440x1100 渲染截图检查通过
```

面板入口：`http://127.0.0.1:8088/eval`

### 3.7 商城 C 端接入

已新增：

- `shang-mall/src/components/AiAssistant.vue`：Web/H5 全局 AI 助手浮窗；
- `shang-mall/src/api/customer-service.ts`：调用 `POST /api/customer-service/chat`；
- `backend/shang-customerservice`：Java 聊天 Controller + Agent 服务代理；
- Spring Security 允许匿名调用聊天接口，订单查询仍靠 `Authorization` 透传判定。

实测：

```text
商城 C 端发问「帮我找一顶露营帐篷」
-> 双人帐篷 防雨款 ¥599-619
-> Agent: ShoppingGuideAgent / 2 次 LLM / 1 次工具

未登录「我的订单到哪了？」
-> status=need_auth，前端显示「去登录查订单」

登录后「我的订单到哪了？」
-> OrderAgent，返回 5 笔订单
```

### 3.8 本地真实接口联调

Agent 服务：`http://127.0.0.1:8088`  
电商后端：`http://127.0.0.1:8086`

实测：

```text
GET /health -> {"status":"UP","llm":"rule-based","graph":"langgraph"}
POST /agent/chat "帮我找一顶露营帐篷"
  -> ShoppingGuideAgent，搜索到「双人帐篷 防雨款」¥599–619
POST /agent/chat "我的订单到哪了？" + 真实 token
  -> OrderAgent，返回 5 笔订单（PENDING_SHIP）
POST /agent/chat "退款一般多久到账？"
  -> KnowledgeAgent，回答 1-3 个工作日
GET /agent/metrics
  -> runs/llm_calls/tool_calls/token/avg_latency
```

trace 实测包含：

- `route` 的 prompt/response；
- `KnowledgeAgent` 的 prompt/response；
- `searchFaq` 工具调用；
- LangGraph 节点事件；
- 输入/输出 token 估算；
- 总延迟。

---

## 4. 待开发

| 项 | 状态 | 说明 |
|---|---|---|
| 真实 LLM 供应商验证 | 已完成 | DeepSeek `deepseek-flash`，8/8 评测通过 |
| pgvector RAG | 已完成 | FAQ 入 pgvector，BAAI/bge-small-zh-v1.5，失败降级关键词；更大知识库/切片/引用待开发 |
| 生产持久化 | 部分完成 | trace/run 已落 PostgreSQL；session/message、大附件、Langfuse 待接 |
| Java 落地 | 待开发 | 当前是 Python Phase-0；生产建议 `shang-customerservice` + Spring AI/LangGraph4j |
| 会话持久化 | 待开发 | SessionStore 仍是内存，重启丢失 |
| 写操作 | 待开发 | 售后/地址修改需要确认令牌、幂等、审计、回滚 |
| 鉴权集成 | 待开发 | 当前透传 Bearer；生产走 identity/JWT 与 RBAC |
| Langfuse/OTel | 待开发 | 当前自建 trace；生产接 Langfuse + OpenTelemetry |
| 100–500 条评测集 | 待开发 | 当前 8 条示例；需从 pytest/禅道/线上 trace 扩充 |
| LLM-as-Judge | 待开发 | 当前是确定性指标；语义质量 judge 待接 |
| SFT/DPO/蒸馏 | 待开发 | 需先积累 trace/反馈/评测集 |
| 可视化评测面板 | 已完成 | `/eval` 只读页面：指标、用例、答案、trace |
| 前端/坐席工作台 | 待开发 | C 端 AI 浮窗已完成；人工坐席工作台未实现 |
| 限流/熔断/队列 | 待开发 | 生产高并发需要 |

---

## 5. 建议的下一步

1. **RAG 增强**：文档切片、更多售后/物流/发票文档、引用展示、召回率评测。
2. **持久化**：把 session/message 迁到 PostgreSQL/Redis，补附件存储与 Langfuse。
3. **Java 落地**：在 `shang-customerservice` 建 Spring AI + LangGraph4j 版本，保持同一 `AgentTask/AgentResult` 契约。
4. **评测集扩充**：从 `pytest_automation/test_cases.json`、禅道用例、线上会话构造 100+ cases。
5. **LLM-as-Judge**：在现有确定性指标上增加语义质量评分。
6. **写操作**：先做“确认令牌 + 幂等 + 审计”的售后/地址，不开放自动退款。

---

## 6. 运行入口

```text
agent_service/README.md
agent_service/app/
agent_service/eval/
```

本地服务：

```bash
cd agent_service
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8088
```
