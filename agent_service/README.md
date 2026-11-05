# ShangPivot Phase-0 Agent Service

基于 **LangGraph** 的 Phase-0 Agent 参考实现：Supervisor + 5 个子 Agent + 工具调用 + trace + 离线评测。

> 这是 Agent 架构的本地可运行验证，不是最终生产运行时。生产建议迁移到 `shang-customerservice`（Spring AI + LangGraph4j）或独立 Agent 服务；待开发项见 [Agent 落地进展](../../docs/03-ai/Agent落地进展.md)。

## 已实现

- LangGraph `StateGraph`：`route → shopping/order_status/after_sale/knowledge/handoff → finalize`
- 子 Agent：
  - `ShoppingGuideAgent`：商品搜索
  - `OrderAgent`：订单查询（需要登录态）
  - `AfterSaleAgent`：售后政策/售后单查询；写操作只到确认边界
  - `KnowledgeAgent`：FAQ 检索
  - `HandoffAgent`：转人工
- 工具层：通过 REST 调 `commerce`，不直读数据库
- 知识库：FAQ 入 pgvector，`searchFaq` 走向量检索；检索失败自动降级关键词
- LLM 网关：
  - 默认 `RuleBasedLlmGateway`（无 API Key 也能验证编排）
  - `OpenAiCompatibleLlmGateway`（配置 `AGENT_LLM_BASE_URL/AGENT_LLM_MODEL/AGENT_LLM_API_KEY_FILE` 后切换）
  - 已用 DeepSeek `deepseek-flash` 完成真实链路验证
- Trace：
  - 每个 run 记录 `intent/agent/status`
  - 每次 LLM 调用记录 prompt、response、token、latency
  - 每次工具调用记录 args、result、status、latency
  - 每次检索记录 backend、query、hits、score、fallback
  - LangGraph callback 记录节点事件
  - 默认输出 `artifacts/agent-traces.jsonl`；`AGENT_TRACE_BACKEND=postgres` 时 run + 完整 trace 落 PostgreSQL，重启后可查
- API：
  - `POST /agent/chat`
  - `GET /agent/runs`
  - `GET /agent/runs/{run_id}`
  - `GET /agent/metrics`
  - `GET /health`
  - `GET /eval` 可视化评测面板
  - `GET /eval/reports` / `GET /eval/reports/{rule|real}`
- 评测：
  - 8 条 golden cases
  - 确定性指标：意图、子 Agent、状态、工具、答案事实、trace 覆盖
  - `eval/run_eval.py`

## 启动

```bash
cd agent_service

# 依赖已安装到 .venv；新环境：
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python fastapi 'uvicorn[standard]' langgraph langchain-core httpx pydantic pytest pytest-asyncio fastembed 'psycopg[binary]'

# 可选：FAQ 入 pgvector（本地 shang-postgres）
.venv/bin/python scripts/ingest_knowledge.py \
  --dsn 'postgresql://<user>:<password>@127.0.0.1:55434/shang'

# 启动（开启 RAG + PostgreSQL trace）
AGENT_RAG_ENABLED=1 \
AGENT_PG_DSN='postgresql://<user>:<password>@127.0.0.1:55434/shang' \
AGENT_TRACE_BACKEND=postgres \
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8088
```

本地电商后端需运行在 `http://127.0.0.1:8086`。未开启 RAG 时 `searchFaq` 使用关键词检索。

## 调用示例

```bash
curl -sS -X POST http://127.0.0.1:8088/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"帮我找一顶露营帐篷"}' | jq
```

查询订单需要带真实登录 token：

```bash
TOKEN=$(curl -sS -X POST http://127.0.0.1:8086/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13900000009","code":"123456","clientType":"web"}' | jq -r '.data.accessToken')

curl -sS -X POST http://127.0.0.1:8088/agent/chat \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"我的订单到哪了？"}' | jq
```

查看 trace：

```bash
curl -sS http://127.0.0.1:8088/agent/runs/<run_id> | jq
```

## 测试与评测

```bash
.venv/bin/python -m pytest -q
.venv/bin/python eval/run_eval.py
```

当前基线：

```text
8 passed
8/8 eval cases passed（规则模型与 DeepSeek 各跑一遍）
intent_accuracy=1.0
agent_accuracy=1.0
status_accuracy=1.0
tool_accuracy=1.0
answer_fact_accuracy=1.0
trace_coverage=1.0
```

真实模型评测：

```bash
AGENT_LLM_BASE_URL=https://api.deepseek.com/v1 \
AGENT_LLM_MODEL=deepseek-flash \
AGENT_LLM_API_KEY_FILE=/Users/imac/.zcode/secrets/deepseek-api-key \
.venv/bin/python eval/run_eval.py --llm openai
```

报告输出到 `eval/report-real.json`。DeepSeek 当前模型列表里 `deepseek-flash` 是 flash 实际模型 id；
`v4.1flash` / `deepseek-v4.1-flash` 会被 API 拒绝（HTTP 400）。

评测支持 `answer_facts`（全部命中）和 `answer_any`（任一命中），避免同义表达被误判。
路由 prompt 带 few-shot；真实模型连续两轮 8/8。

## 目录

```text
agent_service/
├── app/
│   ├── main.py        # FastAPI + AgentRuntime + trace API
│   ├── graph.py       # LangGraph StateGraph
│   ├── agents.py      # Supervisor/子 Agent
│   ├── llm.py         # 规则模型 + OpenAI-compatible 网关（含 key file）
│   ├── tools.py       # commerce REST 工具 + FAQ 检索降级
│   ├── rag.py         # pgvector 入库/检索
│   ├── tracing.py     # trace 数据结构/JSONL/PostgreSQL/callback
│   └── models.py
├── data/faq.json      # Phase-0 知识库
├── scripts/ingest_knowledge.py
├── static/eval.html   # 可视化评测面板
├── eval/
│   ├── cases.jsonl
│   ├── run_eval.py
│   └── report.json
└── tests/test_agent.py
```

## 可视化评测面板

启动服务后打开：

```text
http://127.0.0.1:8088/eval
```

页面包含：

- 规则模型 / DeepSeek 真实模型报告切换；
- 通过率、意图/Agent/工具/事实准确率、平均延迟；
- 8 条用例的输入、实际意图、Agent、状态、耗时、PASS/FAIL；
- 点击用例查看最终回答、期望 vs 实际、工具调用和完整 trace 时间线；
- “运行记录”标签页查看 `/agent/runs`，点击 run 查看 LLM/工具/检索 trace。

面板是本地只读页面，默认只监听 `127.0.0.1`。

## RAG 与 trace 持久化验证

```text
GET /health -> {"rag":"pgvector","rag_error":null,"trace_store":"postgres","trace_error":null}
POST /agent/chat "退款一般多久到账？"
  -> KnowledgeAgent
  -> searchFaq: pgvector, top1 退款到账 score=0.8182
  -> trace.retrievals 记录 backend/query/hits/fallback

重启服务后：
GET /agent/runs/<run_id> -> 仍返回同一 trace
GET /agent/runs -> 从 PostgreSQL 读取
```

## 待开发

- 更大知识库、文档切片与引用展示（当前只入 5 条 FAQ）
- 会话/消息持久化（trace 已落 PostgreSQL；SessionStore 仍是内存）
- Java `shang-customerservice` / Spring AI 落地
- 写操作工具、确认令牌、幂等、审计
- Langfuse/OpenTelemetry 生产观测
- 100–500 条评测集与 CI 门禁
- SFT/DPO/蒸馏数据管道
