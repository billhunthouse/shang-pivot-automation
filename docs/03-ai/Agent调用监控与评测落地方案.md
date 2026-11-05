# Agent 调用监控与评测落地方案

> 目标：Agent 每一次运行都可追溯：用户输入、模型输入、模型输出、工具调用、RAG 命中、状态变化、token/时延/成本；同时建立可版本化、可回归、可上 CI 的评测体系。  
> 范围：以 LangGraph / Spring AI 为例，方案可迁移到其他 Agent 框架。  
> 项目背景：尚品汇电商平台，Java/Spring Boot + PostgreSQL/pgvector + Redis + MinIO。

---

## 1. 先定原则

### 1.1 监控不是“打印日志”

Agent 监控至少要能回答 6 个问题：

1. 这次请求是谁发起的？（`sessionId` / `customerId` / `channel`）
2. 主 Agent 路由到了哪个子 Agent？为什么？
3. 模型实际收到的完整输入是什么？（system prompt、历史、RAG 文档、工具定义）
4. 模型输出了什么？是否解析成功？是否调用了工具？
5. 工具实际入参、出参、耗时、错误是什么？
6. 这次任务成功了吗？失败在哪一步？花了多少 token/时间/成本？

### 1.2 全量元数据 + 分级保存正文

“每一次调用都要监控”不等于“每一次都把完整 prompt 明文存 90 天”。建议：

| 数据 | 策略 |
|---|---|
| trace/span 元数据、模型、耗时、token、工具名、状态 | **100% 采集** |
| 错误请求的完整输入/输出 | **100% 保存**（脱敏后） |
| 正常请求的完整输入/输出 | 默认采样 10–20%；可按会话/租户开启全量 |
| 高敏感字段（手机号、地址、身份证、支付信息） | **落库前脱敏**；原文单独加密存储、短 TTL |
| 评测集 | 只使用脱敏、授权、版本化的数据 |

### 1.3 追踪 ID 必须能串起来

```text
HTTP traceId（W3C traceparent）
  └─ agentRunId（一次用户任务）
      ├─ graphStepId（节点）
      ├─ llmCallId（一次模型调用）
      ├─ toolCallId（一次工具调用）
      └─ retrievalId（一次 RAG 检索）
```

这些 ID 同时写入：

- 应用日志（MDC）；
- SkyWalking / OpenTelemetry span；
- LLM 观测平台（Langfuse/Phoenix）；
- 评测结果表。

---

## 2. 监控数据模型

### 2.1 核心表

| 表 | 作用 | 关键字段 |
|---|---|---|
| `agent_run` | 一次用户任务 | id, trace_id, session_id, customer_id, channel, intent, status, started_at, finished_at, total_tokens, total_cost, error |
| `agent_step` | 图节点/子 Agent 步骤 | id, run_id, parent_step_id, node_name, agent_name, status, input_summary, output_summary, latency_ms, checkpoint_id |
| `llm_call` | 一次模型调用 | id, run_id, step_id, model, prompt_version, input_tokens, output_tokens, latency_ms, finish_reason, status, request_ref, response_ref |
| `tool_call` | 一次工具调用 | id, run_id, step_id, tool_name, args_json, result_json, status, latency_ms, retry_count, idempotency_key |
| `retrieval` | 一次 RAG 检索 | id, run_id, query, top_k, doc_ids, scores, latency_ms, hit |
| `guardrail_event` | 安全/护栏 | id, run_id, type, action, detail, created_at |
| `feedback` | 用户/人工反馈 | id, run_id, type, score, comment, operator |
| `eval_case` | 评测用例 | id, version, input, context, expected, tags, source, pii_level |
| `eval_run` | 一次评测执行 | id, dataset_version, agent_version, prompt_version, model, started_at, status |
| `eval_result` | 单条评测结果 | id, eval_run_id, case_id, metrics_json, passed, judge_reason, latency_ms, cost |

### 2.2 大字段放哪里

- **PostgreSQL**：元数据、索引、状态、token、耗时、成本、错误码、trace 关联；
- **MinIO/S3**：完整 prompt/response、工具原始响应、RAG 文档快照、评测报告；
- **ClickHouse**（规模上来后）：高频 LLM/tool 事件分析；
- **Langfuse**：LLM trace UI、prompt 版本、dataset/experiment、人工标注。

> 不建议把完整 prompt/response 全塞进 PostgreSQL 大字段：查询会变慢，备份会膨胀，权限也不好控。

### 2.3 一次调用的 trace 示例

```json
{
  "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
  "agentRunId": "run_01J...",
  "sessionId": "sess_01J...",
  "customerId": "cust_9001",
  "channel": "web_mall",
  "intent": "order_status",
  "agent": "OrderAgent",
  "steps": [
    {
      "stepId": "step_1",
      "node": "router",
      "latencyMs": 420,
      "llm": {
        "model": "qwen-plus",
        "promptVersion": "router-v3",
        "inputTokens": 812,
        "outputTokens": 36,
        "finishReason": "stop"
      }
    },
    {
      "stepId": "step_2",
      "node": "tool:getOrder",
      "tool": "getOrder",
      "args": {"orderNo": "O202611050001"},
      "status": "ok",
      "latencyMs": 38
    }
  ],
  "status": "success",
  "totalTokens": 1204,
  "totalCost": 0.0021
}
```

---

## 3. LangGraph 埋点方案

### 3.1 一句话方案

**用 LangGraph 的 callback + `RunnableConfig` 元数据 + checkpointer 做全链路采集；用 Langfuse/OTel 做存储和可视化；不要在每个节点里手写重复日志。**

### 3.2 关键 hook

Python LangGraph / LangChain 的 `BaseCallbackHandler` 可以覆盖：

| 回调 | 采集内容 |
|---|---|
| `on_chain_start` | 图/节点开始、输入摘要、parent run |
| `on_chain_end` | 节点输出、耗时、状态 |
| `on_chain_error` | 节点异常、堆栈摘要 |
| `on_chat_model_start` | 模型、messages、temperature、tools schema |
| `on_llm_new_token` | 流式 token（只在需要时聚合，不逐 token 落库） |
| `on_llm_end` | 输出、token usage、finish reason |
| `on_llm_error` | 模型错误、重试次数 |
| `on_tool_start` | 工具名、入参、tool_call_id |
| `on_tool_end` | 工具出参、耗时 |
| `on_tool_error` | 工具异常、错误码 |

### 3.3 绑定上下文

每次调用图时，把业务上下文塞进 `RunnableConfig`：

```text
config = {
  "configurable": {"thread_id": session_id},
  "callbacks": [collector],
  "metadata": {
    "trace_id": ...,
    "session_id": ...,
    "customer_id": ...,
    "channel": ...,
    "agent_name": ...,
    "prompt_version": ...,
    "dataset_version": ...
  },
  "tags": ["prod", "web_mall", "order"]
}
```

这样每一层子调用都能继承 `trace_id/session_id`，不需要在节点里手工传递。

### 3.4 图状态与检查点

- 使用 checkpointer 保存每个 super-step 的状态；
- 记录 `checkpoint_id`、`parent_checkpoint_id`；
- **不要每一步都保存完整 state**：保存 state diff + 关键槽位；
- 失败恢复时用 `checkpoint_id` 重放，不重复执行写工具；
- 写操作前设置 `interrupt` / human-in-the-loop，确认后再继续。

### 3.5 流式事件

- 用 `astream_events(version="v2")` 或等价事件流采集 `on_chat_model_stream`、`on_tool_start`、`on_tool_end`；
- 前端 SSE 与后端观测解耦：观测走异步队列，不阻塞用户流；
- 流式结束后统一写一条 `llm_call`，不要每个 token 一行。

### 3.6 自建 vs 现成

| 方案 | 适合 |
|---|---|
| Langfuse self-host | 需要私有化、prompt 管理、dataset/experiment、人工标注；推荐 |
| LangSmith | 快速接入 SaaS；数据出境/合规需评估 |
| OpenTelemetry + Phoenix | 希望 vendor-neutral、统一 OTel |
| 纯自建 Postgres + MinIO | 数据完全自控；UI/评测要自己写 |

**推荐组合**：OpenTelemetry（服务/工具 span）+ Langfuse self-host（LLM 输入输出/trace/dataset/eval）+ PostgreSQL（业务元数据）+ MinIO（原始 payload）。

---

## 4. Spring AI / Java 侧怎么接

当前项目是 Java/Spring Boot，若用 Spring AI 或 LangGraph4j：

| 能力 | 接入点 |
|---|---|
| 模型调用 | `ChatClient` + 自定义 `Advisor` / `ObservationRegistry` |
| 工具调用 | `ToolCallingManager` / `@Tool` 包装器 |
| MCP | Spring AI MCP Client/Server |
| RAG | `VectorStore` + `QuestionAnswerAdvisor` |
| 记忆 | `ChatMemory` + 会话表 |
| 图编排 | LangGraph4j 节点包装器/checkpoint listener |
| 观测 | Micrometer Observation → OpenTelemetry → SkyWalking/Langfuse |

要点：

- 在 Advisor 里记录 `promptVersion`、model、tokens、latency；
- 工具包装器统一记录入参/出参/耗时/错误；
- 用 `traceId` 把 SkyWalking 的服务 span 与 Langfuse 的 LLM trace 关联；
- 不要把完整 prompt 写进 SkyWalking span（太大且含 PII），只放摘要和 object key。

---

## 5. 采集架构

```text
Agent / LangGraph
   │  callback / advisor
   ▼
本地 buffer（有界队列）
   │  异步、批量、失败重试
   ▼
Collector
   ├─ PII 脱敏
   ├─ token/成本计算
   ├─ prompt/model/tool 版本补全
   ├─ 采样策略
   └─ 分流：
        ├─ PostgreSQL：元数据/指标
        ├─ MinIO：完整 payload
        └─ Langfuse/OTel：trace/评测
```

要求：

- **异步**：采集失败不能影响主请求；
- **有界**：队列满时降级为元数据，丢弃正文并计数；
- **幂等**：同一 `llmCallId` 不重复写；
- **可回放**：payload 带版本和 object key，可重放评测；
- **可删除**：按会话/租户/时间删除，满足隐私要求。

---

## 6. 脱敏、采样与成本

### 6.1 脱敏

落库前统一处理：

- 手机号：`138****0001`
- 地址：保留城市/区，详细地址掩码
- 身份证/银行卡：只留后 4 位
- token/密码/密钥：直接丢弃
- prompt 中的用户原文：可按租户配置“全量/脱敏/仅摘要”

### 6.2 采样

| 场景 | 策略 |
|---|---|
| 正常成功 | 10–20% 完整 payload，100% 元数据 |
| 失败/异常 | 100% 完整 payload |
| 写操作/转人工 | 100% 完整 payload |
| 调试会话 | 会话级开启全量，自动过期 |
| 高 QPS | 动态采样 + 错误偏置 |

### 6.3 成本

- 记录 input/output token、模型单价、缓存命中；
- 按 `agent/node/model/prompt_version` 聚合成本；
- 对“高 token 低价值”的节点做 prompt 压缩/小模型路由；
- 设置单会话 token 预算和单日租户预算。

---

## 7. 看板与告警

### 7.1 核心指标

| 类别 | 指标 |
|---|---|
| LLM | 调用量、P95 延迟、首 token 延迟、token 数、成本、空响应、JSON 解析失败、重试 |
| Tool | 调用量、成功率、P95、超时、重试、幂等冲突 |
| Agent | 任务成功率、平均步数、循环次数、转人工率、误转人工率 |
| RAG | 召回率、引用覆盖率、无命中率、groundedness |
| 安全 | 注入拦截、PII 泄露、越权、敏感输出 |
| 业务 | 解决率、重复咨询率、转化率、满意度 |

### 7.2 告警

- 模型错误率 > 5%；
- 工具错误率 > 3%；
- Agent 循环 > 5 步；
- 首 token P95 > 3s；
- 单会话 token > 预算；
- 写工具未确认执行（应为 0）；
- 评测通过率环比下降 > 2%。

---

## 8. 评测集从哪里来

### 8.1 六个来源

| 来源 | 说明 | 优先级 |
|---|---|---|
| 现有 pytest 845 条用例 | 已有业务场景、断言、优先级 | 高 |
| 禅道用例/Bug | 真实缺陷、边界、回归 | 高 |
| 历史客服会话/工单 | 真实问法、失败案例 | 高（需脱敏/授权） |
| 知识库/FAQ/政策 | 生成 QA 对、引用评测 | 高 |
| 人工构造 | 多轮、缺槽、写操作、对抗 | 高 |
| LLM 合成 | 扩充问法/变体，必须人工审核 | 中 |

### 8.2 从 pytest 用例转 Agent 评测

以 `API-ORDER-001` 为例：

```text
pytest 场景：购物车提交订单
→ 用户话术：“我购物车里的东西想下单，怎么弄？”
→ 期望：intent=order_submit；工具 getCart → submitOrder；写操作需确认
→ 断言：不提前下单；确认后才调用；订单状态 PENDING_PAY
```

不是把 pytest 断言照搬，而是把“接口行为”翻译成“用户语言 + 期望轨迹”。

### 8.3 从线上 trace 转评测

筛选：

- 用户点踩/转人工/重复追问；
- 工具失败/模型解析失败；
- 高延迟/高 token；
- 写操作被拒绝/回滚；
- 人工坐席修改过的回复。

脱敏后进入候选池，人工标注后入评测集。

### 8.4 评测集规模

| 阶段 | 规模 |
|---|---|
| 启动 | 100–200 条 |
| 稳定期 | 300–500 条 |
| 发布回归 | 每次跑全量；PR 跑核心 100 条 |
| 对抗/安全 | 50–100 条独立集合 |

分布建议：

- 60% 常见单轮；
- 25% 多轮/缺槽/追问；
- 10% 写操作/确认/拒绝；
- 5% 对抗/注入/越权。

---

## 9. 评测集 Schema

每条 case 至少包含：

```json
{
  "caseId": "EVAL-ORDER-001",
  "version": 3,
  "source": "pytest:API-ORDER-001",
  "tags": ["order", "read", "multi_turn"],
  "difficulty": "P1",
  "messages": [
    {"role": "user", "content": "我上周买的鞋到哪了？"}
  ],
  "context": {
    "customerId": "cust_9001",
    "channel": "web_mall",
    "locale": "zh-CN",
    "mockTools": ["getOrder", "getLogistics"]
  },
  "expected": {
    "intent": "order_status",
    "toolCalls": [
      {"name": "getOrder", "args": {"orderNo": "O202611050001"}},
      {"name": "getLogistics", "args": {"orderNo": "O202611050001"}}
    ],
    "answerFacts": ["运输中", "预计明天送达"],
    "citations": ["logistics-policy#v2"],
    "forbidden": ["已签收"],
    "handoff": false,
    "requiresConfirmation": false
  },
  "pii": "redacted"
}
```

### 9.1 版本与切分

- `dataset_version`：每次新增/修改必须升版本；
- 固定切分：`dev` / `validation` / `test`；
- 防止训练/评测泄漏：SFT 数据与 test 集去重；
- 每次评测记录 `dataset_version + agent_version + prompt_version + model`。

---

## 10. 怎么评测

### 10.1 四层评测

| 层 | 评什么 | 方法 |
|---|---|---|
| 组件级 | prompt 解析、工具 schema、RAG 检索 | 单元测试 + 确定性断言 |
| 轨迹级 | 意图、槽位、工具选择、参数、步数 | 与期望轨迹对比 |
| 结果级 | 回答事实、引用、语气、安全 | 规则 + LLM judge + 人工 |
| 业务级 | 解决率、转人工率、转化、成本 | 线上 A/B / 灰度 |

### 10.2 确定性指标

- 意图准确率：`intent == expected.intent`；
- 工具选择：名称集合/顺序匹配；
- 参数准确率：JSON 字段级 exact/F1；
- JSON Schema 合法率；
- 槽位完整率；
- 检索 Recall@K / MRR；
- 引用命中率；
- 禁用词/敏感信息命中；
- 是否在确认前执行写工具（必须为 0）；
- 步数/工具调用次数是否超预算；
- 延迟/成本。

### 10.3 LLM-as-Judge

适合：回答质量、语气、帮助性、引用一致性。  
不适合：精确工具参数、金额、订单状态（优先确定性断言）。

Judge 设计：

- 给 rubric，不给“标准答案全文”；
- 0–4 分或 1–5 分，维度拆开；
- 多 judge/温度 0，降低位置偏差；
- 人工校准 30–50 条，计算 judge 与人工一致性；
- 高风险场景人工复核；
- 记录 judge prompt/model/version，保证可复现。

示例 rubric：

| 维度 | 0 | 2 | 4 |
|---|---|---|---|
| 事实正确 | 关键事实错误 | 部分正确 | 全部正确 |
| 引用 | 无引用/错引 | 有引用但不完整 | 引用准确 |
| 任务完成 | 未解决 | 部分解决 | 完整解决 |
| 安全 | 越权/泄露 | 有风险 | 安全 |

### 10.4 多轮评测

- 用脚本模拟用户：缺槽→补槽→确认→完成；
- 断言每轮状态：`NEED_SLOT`、`WAIT_CONFIRM`、`ANSWERED`；
- 断言不重复调用工具、不提前写、不丢失上下文；
- 超长对话测上下文压缩/摘要。

### 10.5 写操作评测

- 沙箱环境 + 测试账号；
- 断言：确认前无写工具；确认后有且仅有一次；
- 幂等键重复提交不产生重复订单；
- 失败回滚/补偿；
- 越权访问他人订单必须拒绝。

### 10.6 RAG 评测

- 检索：Recall@K、MRR、无命中率；
- 生成：faithfulness、answer relevancy、citation correctness；
- 拒答：知识不足时是否明确说不知道/转人工；
- 时效：政策更新后旧答案是否失效。

---

## 11. 评测执行架构

```text
eval dataset (Postgres/JSONL, versioned)
   │
   ▼
eval runner (pytest / promptfoo / DeepEval / Ragas / Langfuse experiments)
   ├─ mock tools（回放真实工具响应）
   ├─ sandbox tools（隔离环境）
   ├─ LLM judge
   └─ deterministic assertions
   │
   ▼
eval_result (Postgres) + report (Allure/HTML)
   │
   ▼
CI gate / dashboard / regression compare
```

建议：

- **PR 阶段**：核心 100 条 + 工具契约 + 安全用例，5–10 分钟；
- **合并/夜间**：全量 300–500 条 + 真实 sandbox；
- **发布前**：全量 + 对抗集 + 人工抽检；
- **线上**：采样 trace + 用户反馈 + 人工标注。

工具选择：

| 工具 | 用途 |
|---|---|
| pytest | 确定性断言、CI 集成 |
| promptfoo | prompt/agent 对比、红队、CI |
| DeepEval | 指标化评测、LLM judge |
| Ragas | RAG 专项指标 |
| Langfuse | trace、dataset、experiment、人工标注 |
| Allure | 现有测试报告统一展示 |

---

## 12. CI 门禁与发布

建议门禁：

```text
单元测试
  → 工具 schema/契约测试
  → 核心评测集（100 条）
  → 安全/对抗集
  → 性能冒烟（P95/成本）
  → 人工抽检（高风险变更）
```

阻断条件示例：

- 任务成功率环比下降 > 2%；
- 工具参数准确率 < 95%；
- 写操作未确认执行 > 0；
- 严重安全违规 > 0；
- P95 首 token > 3s；
- 单任务成本上涨 > 20%。

---

## 13. 线上评测

- **灰度**：5% → 20% → 50% → 100%；
- **影子模式**：新 Agent 只生成不执行，和旧策略对比；
- **A/B**：任务成功率、转人工率、重复咨询率、转化率、成本；
- **采样人工评审**：每周抽 50–100 条；
- **用户反馈**：点赞/点踩、转人工、追问、会话结束原因；
- **漂移监控**：意图分布、工具分布、知识命中率、模型版本。

---

## 14. 分阶段落地

### Phase 1：能看见（1–2 周）

- [ ] 定义 trace/session/run/llm/tool ID；
- [ ] LangGraph callback 或 Spring AI Advisor 接入；
- [ ] 100% 元数据 + 错误全量 + 正常采样；
- [ ] Langfuse/OTel + Postgres/MinIO；
- [ ] 一张 trace 详情页 + 一张总览看板。

验收：任取一次请求，能看到完整调用树、模型输入输出、工具入参出参、耗时/token。

### Phase 2：能评测（2–3 周）

- [ ] 100 条 golden cases（pytest + 禅道 + 人工）；
- [ ] 评测 runner + 确定性指标；
- [ ] LLM judge + 人工校准；
- [ ] CI 跑核心集；
- [ ] 评测报告。

验收：每次 prompt/模型/工具变更都有评测结果和回归对比。

### Phase 3：能闭环（3–4 周）

- [ ] 线上 trace 采样入候选集；
- [ ] 人工标注/反馈闭环；
- [ ] SFT/DPO 数据导出；
- [ ] 灰度/A/B；
- [ ] 成本/延迟/安全告警。

验收：评测集持续增长，发布有门禁，线上有回归。

---

## 15. 常见坑

| 坑 | 规避 |
|---|---|
| 只记录最终回答，没记录模型输入 | 在 `on_chat_model_start` / Advisor 记录 messages + tools |
| 只记录 LLM，不记录工具 | 工具包装器统一埋点 |
| 流式每个 token 写一行 | 聚合为一次 llm_call |
| 把完整 prompt 写进 SkyWalking span | 只放摘要 + object key；完整 payload 进 MinIO/Langfuse |
| 评测集和训练集混用 | 固定切分 + 去重 + 版本化 |
| LLM judge 当唯一标准 | 确定性断言优先；judge 只评语义质量 |
| 只测单轮 | 多轮/缺槽/确认/转人工必须覆盖 |
| 写操作评测污染数据 | 沙箱 + 幂等 + 回滚 |
| 没有版本 | prompt/model/dataset/code 四版本必须记录 |

---

## 16. 一句话总结

**监控层要回答“模型看到了什么、说了什么、调了什么工具、花了多少”；评测层要回答“这次变更是否真的更好、是否更安全、是否更便宜”；两层用同一套 trace/ID/版本串起来，才能形成可落地的 Agent 工程闭环。**
