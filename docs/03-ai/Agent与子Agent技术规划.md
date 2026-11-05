# 电商项目 Agent 与子 Agent 应用规划

> 参考：高德「Agent 后端开发工程师」岗位要求  
> 项目：尚品汇电商平台（Spring Boot 4 + PostgreSQL/pgvector + Redis + MinIO）  
> 日期：2026-11-05  
> 说明：本文只做技术调研、架构规划和落地路线，不写代码、不改现有业务。

---

## 0. 结论先行

### 0.1 推荐方案

不要一上来做“大而全的多 Agent 自治集群”。推荐：

```text
1 个 Supervisor（主 Agent / 编排器）
  + 5 个有明确边界的子 Agent
  + 1 个统一 Tool Gateway（工具网关）
  + 1 个 RAG / 知识库
  + 1 套状态、审计、评测、降级体系
```

首期只做**客服/导购读链路**；写操作（改地址、发起售后）必须“确认 + 幂等 + 可回滚 + 人工兜底”。

### 0.2 技术选型建议

| 层 | 建议 | 理由 |
|---|---|---|
| Agent 运行时 | **Spring AI 2.x + LangGraph4j（或显式状态机）** | 项目是 Java/Spring Boot；Spring AI 原生支持 ChatClient、Tool Calling、MCP、PGVector、Observability；LangGraph4j 补状态图/检查点/人工介入 |
| 工具协议 | **MCP** | 已有 `zentao_mcp` 实践；MCP 适合“模型调用工具”，边界清晰、可复用 |
| Agent 间协议 | 先内部 Java 接口；跨服务/跨团队再考虑 **A2A** | 模块化单体内部用进程内接口最稳；A2A 适合 opaque agent 之间互操作 |
| 模型 | 先第三方 LLM API，后按评测决定 SFT/蒸馏 | 不要在没有评测集和日志前微调 |
| 数据/评测 | PostgreSQL + pgvector + MinIO + 评测集 + Langfuse/Phoenix 类观测 | 复用现有技术栈；先把数据闭环跑通 |
| 训练/蒸馏 | Python 侧独立工具链（PEFT/TRL/vLLM） | 训练与在线 Java 运行时分离，避免污染主应用 |

### 0.3 最重要的三个判断

1. **先做“可评测的 Agent”，再做“更聪明的 Agent”**：没有 golden set、工具调用日志和失败分类，SFT/DPO 没有意义。
2. **子 Agent 不是越多越好**：每个子 Agent 必须有独立职责、独立工具权限、独立超时和失败兜底。首期 4–5 个足够。
3. **写操作不能交给模型直接执行**：模型只能提出“计划”，执行前必须经过策略校验、用户确认、幂等键和审计。

> 调用监控、输入输出留存、评测集构建与 CI 评测的细化方案见 [Agent 调用监控与评测落地方案](Agent调用监控与评测落地方案.md)。
>
> Phase-0 已实践内容与待开发项见 [Agent 落地进展](Agent落地进展.md)。

---

## 1. 招聘要求拆解与项目映射

| 高德岗位要求 | 本质能力 | 在电商项目中的映射 |
|---|---|---|
| 子 Agent 架构设计、调用链路、状态管理、容错降级 | 多 Agent 编排 | Supervisor + 订单/售后/导购/知识子 Agent；状态机 + 检查点 + 超时/重试/降级 |
| 与主 Agent 协议对接、能力编排、多轮对话、工具调用、跨场景任务 | Agent 协议与 Tool Calling | 统一 `AgentTask/AgentResult` 契约；工具网关；多轮槽位；跨订单+售后+推荐协同 |
| 手机端/车机端统一能力出口、地区差异化 | 多端/多区域适配 | Web/H5/管理端客服工作台/内部 QA 控制台；ChannelProfile 描述能力、语言、权限、时延 |
| SFT / Preference Optimization、数据构建 | 模型数据与微调 | 会话、工具日志、失败案例、人工反馈形成训练数据；先评测后 SFT/DPO |
| 模型压缩、蒸馏、推理优化 | 成本/时延优化 | 小模型做意图路由/FAQ，大模型做复杂决策；vLLM/TGI 评估 |
| 工具使用策略、弱网、高并发、复杂上下文 | 鲁棒性 | 工具 schema、超时、熔断、幂等、上下文压缩、流式返回、规则兜底 |
| 复杂出行任务（跨城/多目的地/充电规划） | 复杂任务规划 | 电商类比：退货+换货+替代推荐+催物流+优惠券组合任务 |

> 不能直接照搬出行域。把“路线/POI/路况”替换为“商品/库存/订单/物流/售后/优惠”，把“车机端”抽象为一种低时延、语音优先的 ChannelProfile。

---

## 2. 当前项目基线

### 2.1 已有能力

| 能力 | 现状 | 对 Agent 的价值 |
|---|---|---|
| 模块化单体 | identity / commerce / customer-service 三个上下文 | Agent 放在 `shang-customerservice`，不破坏边界 |
| 商品/购物车/订单/支付/售后 | commerce 已有 REST API 与领域服务 | 天然的工具层 |
| 身份/RBAC/JWT | identity 已有 | Agent 鉴权、顾客隔离、坐席权限 |
| PostgreSQL + pgvector | 已选型，向量表待 V3 启用 | RAG 不需要另引向量库 |
| Redis / MinIO | 已用于缓存、对象存储 | 会话短期状态、知识库附件 |
| ZenTao MCP | 已有产品/用例/Bug 查询与写入 | 内部 QA Agent 的工具 |
| SkyWalking | 已有服务/端点/Trace/SQL | 内部 Ops Agent 的观测工具 |
| pytest / k6 | 845 条自动化用例、k6 压测 | Agent 回归评测、工具接口压测 |
| 现有 V3.0 设计 | 会话/消息/工单/RAG/转人工已有文档 | 本轮规划的直接基线 |

### 2.2 当前缺口

- `shang-customerservice` 仍是空壳，没有会话、消息、工具调用、RAG；
- 没有主 Agent/子 Agent 编排协议；
- 没有工具网关和工具权限模型；
- 没有 Agent 评测集、trace、token/成本观测；
- 没有模型数据管道和 SFT/DPO/蒸馏流程；
- 没有多端 ChannelProfile；
- 没有写操作的确认、幂等、审计闭环。

### 2.3 架构约束

来自 `ADR-0001` / `ADR-0002`：

1. 模块化单体，不先拆微服务；
2. 跨上下文只走 `*-api`，不跨 schema 直读；
3. Java 21 / Spring Boot 4；
4. PostgreSQL + pgvector、Redis、MinIO；
5. 当前没有独立网关进程。

> 因此首期 Agent 应落在 `shang-customerservice` 内，进程内调用 commerce API；不要为了“像大厂”先拆成多个 Agent 微服务。

---

## 3. 业务场景规划

### 3.1 C 端消费者

| 场景 | 示例 | Agent 能力 |
|---|---|---|
| 导购 | “找 500 元以内通勤鞋，明天能到” | 商品搜索、库存、时效、对比、推荐 |
| 订单 | “我的订单到哪了？” | 订单查询、物流、异常解释 |
| 售后 | “鞋不合脚，想退货” | 售后政策 RAG、售后单创建、工单 |
| 账户 | “改一下收货地址” | 地址查询/修改（写操作需确认） |
| 复杂任务 | “退货，同时推荐一双替代款，最好明天到” | 多子 Agent 协同：售后 + 商品 + 物流 |

### 3.2 管理端/客服坐席

| 场景 | Agent 能力 |
|---|---|
| 会话摘要 | 自动总结用户诉求、已尝试动作、待办 |
| 建议回复 | 基于知识库和订单上下文生成候选回复 |
| 工单分流 | 按技能组、SLA、情绪、风险路由 |
| 知识缺口 | 统计未命中问题，反哺知识库 |

### 3.3 内部 QA / Ops（差异化亮点）

利用现有资产做“内部 Agent”，比单纯客服 Agent 更能体现工程能力：

| 场景 | 工具 |
|---|---|
| 失败用例归因 | pytest 结果 + Allure 截图 + SkyWalking trace |
| 缺陷查重/建单 | ZenTao MCP 查询/创建 Bug |
| 慢接口分析 | SkyWalking endpoint/SQL Span |
| 发布风险评估 | 最近测试结果 + 缺陷 + 变更范围 |
| 测试用例生成 | 现有 845 条用例库 + 接口契约 |

> 这条线和高德岗位的“工具调用、复杂任务、稳定性”高度相关，也最容易在面试中讲出工程深度。

---

## 4. 目标架构

```text
┌─────────────────────────────────────────────────────────────┐
│ 渠道层                                                       │
│  Web / H5 / 管理端客服工作台 / 内部 QA 控制台 / 未来车机语音  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│ Agent Gateway                                                │
│  鉴权 / 顾客隔离 / 限流 / SSE 流式 / PII 脱敏 / TraceId      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│ Supervisor（主 Agent / 编排器）                              │
│  意图识别 / 任务规划 / 子 Agent 路由 / 预算 / 护栏 / 汇总     │
│  状态机 + 检查点 + 人工确认 + 失败降级                       │
└───────┬──────────────┬──────────────┬──────────────┬────────┘
        │              │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐ ┌────▼─────────┐
│ 导购 Agent    │ │ 订单 Agent │ │ 售后 Agent │ │ 知识/FAQ Agent│
│ 搜索/推荐/对比│ │ 订单/物流  │ │ 退换/工单  │ │ RAG/政策/引用 │
└───────┬──────┘ └─────┬──────┘ └─────┬──────┘ └────┬─────────┘
        └──────────────┴──────────────┴──────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│ Tool Gateway（统一工具网关）                                 │
│  commerce API / identity / RAG / MCP / 外部系统               │
│  权限 / schema / 超时 / 重试 / 幂等 / 审计 / 限流             │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  commerce 领域 API    ZenTao MCP        SkyWalking / k6
  PostgreSQL/pgvector  Redis / MinIO      LLM Provider
```

### 4.1 分层原则

1. **Supervisor 拥有状态**；子 Agent 尽量无状态，输入 `AgentContext`，输出 `AgentResult`。
2. **子 Agent 不直接访问数据库**，只通过工具网关调用 commerce `*-api`。
3. **工具网关是唯一执行面**：模型不能拼 SQL、不能任意发 HTTP。
4. **写操作必须确认**：模型生成计划，网关校验权限和幂等键，前端/用户确认后执行。
5. **每一跳可观测**：`traceId + sessionId + agentRunId + toolCallId` 贯穿 LLM、工具、后端。

---

## 5. 子 Agent 设计

### 5.1 首期建议只做 5 个

| 子 Agent | 职责 | 主要工具 | 写操作 |
|---|---|---|---|
| `ShoppingGuideAgent` | 商品搜索、对比、推荐、库存/时效 | `searchProducts`、`getProduct`、`getStock`、`getDeliveryEta` | 否 |
| `OrderAgent` | 订单状态、物流、取消/确认收货 | `getOrder`、`getLogistics`、`cancelOrder`、`confirmReceive` | 取消需确认 |
| `AfterSaleAgent` | 退换货政策、售后单、工单 | `getAfterSalePolicy`、`createAfterSale`、`createTicket` | 需确认 |
| `KnowledgeAgent` | FAQ/政策/活动规则 RAG | `searchKnowledge`、`getDoc` | 否 |
| `HandoffAgent` | 转人工、坐席排队、会话摘要 | `escalateToHuman`、`createTicket` | 是（人工接管） |

> `HandoffAgent` 也可以不做成独立 Agent，而由 Supervisor 的“转人工策略”实现；首期建议作为策略，不增加一个 LLM 调用。

### 5.2 每个子 Agent 的契约

每个子 Agent 都必须声明：

```text
name
description
allowed_intents
allowed_tools
max_tool_steps
timeout_ms
requires_confirmation
fallback_policy
```

子 Agent 输出必须包含：

- `status`：`ok / need_user_input / need_confirmation / handoff / failed`
- `answer`：面向用户的回答
- `citations`：知识来源
- `tool_calls`：实际调用与结果摘要
- `confidence`：置信度
- `handoff_reason`：转人工原因
- `usage`：token、耗时、模型

### 5.3 子 Agent 的边界

- 不跨域：订单 Agent 不直接查商品表，售后 Agent 不直接改订单状态；
- 不递归：子 Agent 不再调用其他子 Agent，跨域由 Supervisor 编排；
- 不无限循环：最多 3 次工具调用、1 次重规划；
- 不越权：工具网关按 `customerId + role + channel` 过滤；
- 不静默失败：失败必须返回可解释原因，必要时转人工。

---

## 6. 主 Agent 协议与编排

### 6.1 任务契约（概念）

```json
{
  "taskId": "task_xxx",
  "sessionId": "sess_xxx",
  "customerId": "cust_xxx",
  "channel": "web_mall",
  "locale": "zh-CN",
  "intent": "after_sale",
  "slots": {
    "orderNo": "O2026...",
    "reason": "不合脚"
  },
  "constraints": {
    "deadlineMs": 8000,
    "maxToolSteps": 3,
    "allowedTools": ["getOrder", "getAfterSalePolicy", "createAfterSale"]
  },
  "traceId": "..."
}
```

```json
{
  "status": "need_confirmation",
  "answer": "可以为订单 O2026... 发起退货，预计退款 299 元，是否确认？",
  "toolCalls": [],
  "citations": ["after-sale-policy#v3"],
  "confidence": 0.86,
  "handoff": false,
  "usage": {"tokens": 812, "latencyMs": 1240}
}
```

### 6.2 状态机

```text
NEW
  → ROUTING（意图识别）
  → NEED_SLOT（缺参数，追问）
  → PLANNING（拆任务）
  → TOOL_CALLING（只读工具，可并行）
  → WAIT_CONFIRM（写操作）
  → ANSWERING（汇总/引用）
  → ESCALATED（转人工）
  → CLOSED
```

每个状态写入检查点（PostgreSQL），支持断点恢复、重试和审计。

### 6.3 编排策略

| 任务 | 编排 |
|---|---|
| 单域只读 | 直接路由到 1 个子 Agent |
| 多域只读 | Supervisor 并行调用（如商品 + 库存 + 时效） |
| 写操作 | 先只读确认，再 `WAIT_CONFIRM`，确认后执行 |
| 失败 | 1 次重试 + 降级到规则/FAQ/人工 |
| 复杂任务 | 计划 → 逐步执行 → 每步检查 → 汇总 |

示例：

```text
“退货，同时推荐一双替代款，最好明天到”
  → AfterSaleAgent：查订单/售后政策
  → ShoppingGuideAgent：查替代商品/库存
  → DeliveryAgent（可并入 OrderAgent）：查时效
  → Supervisor：汇总方案，等待用户确认退货
```

### 6.4 协议选择

| 场景 | 协议 |
|---|---|
| Java 进程内子 Agent | 内部接口 / 事件，最低延迟 |
| 模型调用工具 | MCP（或 Spring AI Tool Calling） |
| 跨团队/跨语言 Agent | A2A；首期不引入 |
| 前端流式 | SSE / WebSocket，按渠道能力选择 |

> MCP 解决“Agent 用工具”，A2A 解决“Agent 找 Agent”。不要把两者混为一谈。

---

## 7. 工具层规划

### 7.1 工具目录（首期）

| 工具 | 类型 | 说明 |
|---|---|---|
| `searchProducts` | 读 | 关键词/类目/价格/排序 |
| `getProduct` | 读 | 商品详情 + SKU + 库存 |
| `getStock` | 读 | 可售库存 |
| `getDeliveryEta` | 读 | 时效（可先规则模拟） |
| `getOrder` | 读 | 订单状态/金额 |
| `getLogistics` | 读 | 物流轨迹 |
| `cancelOrder` | 写 | 取消待支付订单，需确认 |
| `confirmReceive` | 写 | 确认收货，需确认 |
| `createAfterSale` | 写 | 发起售后，需确认 |
| `createTicket` | 写 | 转人工工单 |
| `searchKnowledge` | 读 | RAG 检索，带引用 |
| `queryTestBugs` | 读 | 内部 QA：禅道 Bug |
| `queryTrace` | 读 | 内部 Ops：SkyWalking |

### 7.2 工具契约

每个工具必须有：

- JSON Schema（参数、必填、枚举、长度）；
- 权限（顾客/坐席/管理员）；
- 读/写标记；
- 超时（读 1s、写 3s）；
- 幂等键（写工具）；
- 错误码（业务错误 vs 系统错误）；
- 审计字段（谁、何时、入参摘要、结果摘要、traceId）。

### 7.3 MCP 的定位

- **对外**：把 commerce/identity 能力封装成 MCP Server，供其他 Agent/IDE/内部工具调用；
- **对内**：客服 Agent 可直接用 Spring AI Tool Calling，减少一跳；
- **复用**：现有 `zentao_mcp` 作为 QA Agent 的工具；SkyWalking 查询脚本封装为 MCP 工具；
- **不做什么**：不让模型直接连数据库，不暴露任意 SQL/HTTP。

---

## 8. 多端与地区差异

### 8.1 ChannelProfile

| 渠道 | 流式 | 富卡片 | 语音 | 最大长度 | 写权限 | 时延目标 |
|---|---|---|---|---|---|---|
| Web 商城 | 是 | 是 | 否 | 长 | 是（确认） | 首字 <2s |
| H5 | 是 | 是 | 否 | 中 | 是（确认） | 首字 <2s |
| 管理端坐席 | 是 | 是 | 否 | 长 | 是（人工确认） | <3s |
| 内部 QA 控制台 | 是 | 表格 | 否 | 长 | 只读/建单 | <3s |
| 未来车机/语音 | 是 | 否 | 是 | 短 | 语音确认 | 首字 <1.5s |

### 8.2 地区差异

- 语言/币种/运费规则/售后政策按 `locale + region` 配置；
- 工具返回统一 DTO，渠道适配器负责格式化；
- 不同地区的能力开关（如某些地区不支持某支付方式）；
- 不在 prompt 里硬编码政策，统一走 RAG/配置。

---

## 9. RAG / 知识库

### 9.1 知识来源

- 售后政策、退换货规则；
- FAQ、活动规则；
- 商品问答/参数解释；
- 客服快捷回复；
- 内部 QA：接口契约、测试规范、故障 Runbook。

### 9.2 检索链路

```text
文档 → 清洗 → 切片 → embedding → pgvector
问题 → 向量检索 topK →（可选 BM25 混合）→ 重排 → 引用拼装 → LLM
```

建议：

- 切片 300–600 字，保留标题/章节路径；
- 混合检索：pgvector + PostgreSQL `tsvector`/trigram；
- 只检索 `status=发布 && vectorStatus=已向量化`；
- 输出必须带引用；低置信度触发“没找到/转人工”；
- 知识文档版本化，支持增量重建；
- 对政策类问题设置更高的召回阈值。

### 9.3 评测

- 命中率/召回率；
- 引用正确率；
- groundedness（回答是否有依据）；
- 拒答率/转人工率；
- 端到端任务成功率。

---

## 10. 模型与数据：SFT / DPO / 蒸馏

### 10.1 不要先微调

顺序建议：

```text
Prompt Engineering
  → Tool Calling + RAG
  → 评测集 + 失败分类
  → SFT（只在意图/工具 JSON/风格稳定上做）
  → DPO（偏好/安全/语气）
  → 蒸馏（路由/FAQ 小模型）
```

没有稳定的评测集之前，SFT 只会把问题“训进去”。

### 10.2 数据管道

采集：

- 会话消息（用户/助手/工具）；
- 工具调用入参/结果/耗时/错误；
- 用户反馈（点赞/点踩/转人工/解决）；
- 人工坐席修改后的回复；
- 失败 trace + 最终处置。

存储：

- PostgreSQL：结构化会话/工具/反馈；
- MinIO：原始日志、附件、导出数据集；
- 训练数据版本：`dataset_version + prompt_version + model_version`。

脱敏：

- 手机号、地址、身份证、订单号做掩码/哈希；
- 训练集与线上数据分离；
- 保留数据来源和授权记录。

### 10.3 SFT/DPO/蒸馏的适用点

| 技术 | 适用 | 不适用 |
|---|---|---|
| SFT/LoRA | 意图分类、槽位抽取、工具调用 JSON、固定话术 | 频繁变化的政策知识 |
| DPO | 语气、简洁度、拒答/转人工偏好 | 事实性知识（应走 RAG） |
| 蒸馏 | 意图路由、FAQ、简单导购；边缘/低成本 | 复杂多步决策 |
| 量化/推理优化 | 降低成本/时延 | 需要高精度复杂推理的场景 |

### 10.4 模型路由

```text
简单意图/FAQ → 小模型/规则
复杂多步/写操作 → 大模型
高风险/低置信度 → 人工
```

模型路由的收益通常比“全部换大模型”更大。

---

## 11. 稳定性、弱网与高并发

| 问题 | 设计 |
|---|---|
| LLM 慢 | 流式输出；首字目标 <2s；超时降级 |
| 工具慢 | 读工具 1s、写工具 3s；并行只读；熔断 |
| 弱网 | SSE 断线重连；短回答；缓存常见 FAQ |
| 高并发 | 无状态子 Agent；Redis 会话；限流；队列；模型供应商配额 |
| 上下文过长 | 摘要 + 槽位状态 + 只保留最近 N 轮 + RAG topK |
| 模型失败 | 规则/FAQ 兜底；转人工 |
| 工具失败 | 重试 1 次；幂等；返回可解释错误 |
| 写操作重复 | 幂等键 + 状态校验 + 确认令牌 |
| 热点订单/库存 | 不把高并发写暴露给 Agent；走现有交易链路和限流 |

---

## 12. 安全与合规

- 顾客只能访问自己的订单/会话；坐席按技能组和分配访问；
- 工具网关做 RBAC + 数据级过滤，不依赖 prompt；
- PII 脱敏、日志脱敏、训练数据脱敏；
- Prompt injection 防护：工具参数白名单、系统提示隔离、输出过滤；
- 写操作二次确认 + 审计 + 可撤销；
- 不把内部 prompt、密钥、数据库结构暴露给模型；
- 记录模型版本、prompt 版本、工具版本，支持回溯；
- 高风险场景（退款纠纷、投诉、法律）直接转人工。

---

## 13. 可观测与评测

### 13.1 Trace

每次请求记录：

```text
traceId
sessionId
agentRunId
intent
subAgent
toolCalls[]
model
promptVersion
tokensIn/tokensOut
latencyMs
status
handoffReason
```

可接：

- OpenTelemetry / SkyWalking：工具调用后端链路；
- Langfuse / Phoenix：LLM trace、prompt、评测；
- 自定义看板：任务成功率、转人工率、工具失败率、P95。

### 13.2 评测集

建议从三个来源构建 200–500 条 golden cases：

1. 现有 pytest 845 条用例中的业务场景；
2. 历史客服问题/工单；
3. 人工构造的边界/对抗问题。

指标：

- 意图准确率；
- 槽位完整率；
- 工具选择准确率/参数正确率；
- 任务成功率；
- 引用正确率/groundedness；
- 平均轮次、P95 延迟、token 成本；
- 转人工率、误转人工率；
- 安全违规率。

### 13.3 CI 门禁

```text
单元测试 → 工具契约测试 → Agent 评测集 → 安全红队 → 人工抽检
```

任何 prompt/模型/工具变更都必须跑评测，不能只看“感觉更聪明”。

---

## 14. 技术选型对比

| 方案 | 语言 | 优势 | 风险 | 建议 |
|---|---|---|---|---|
| **Spring AI 2.x** | Java | Spring Boot 原生；ChatClient、Tool Calling、MCP、PGVector、Observability | 图编排能力弱于 LangGraph | **首选运行时** |
| **LangChain4j** | Java | AI Services、工具、MCP、RAG 成熟 | 与 Spring 生态整合需额外设计 | 备选 |
| **LangGraph4j** | Java | 状态图、检查点、人工介入；可与 Spring AI 集成 | 社区较小（约 2k stars） | **首选编排补充** |
| LangGraph (Python) | Python | 多 Agent/状态图最成熟；生态大 | 多语言运维；与 Java 主应用割裂 | 原型/训练侧参考 |
| OpenAI Agents SDK | Python | handoff、guardrails、sessions、tracing 概念清晰 | Python 运行时；供应商倾向 | 设计参考/原型 |
| AutoGen | Python | 多 Agent 对话/群聊 | 生产化需大量封装 | 研究参考 |
| CrewAI | Python | 角色/任务抽象快 | 复杂状态控制弱 | 快速原型 |
| Google ADK | Python | 多 Agent、评测、部署工具链 | 与现有 Java 栈割裂 | 研究参考 |
| Dify/Coze | 低代码 | 快速搭 RAG/工作流 | 深度定制/权限/事务弱 | Demo/POC |

### 14.1 推荐组合

```text
shang-customerservice（Java）
  ├─ Spring AI：模型、工具、MCP、RAG、观测
  ├─ LangGraph4j：Supervisor 状态图/检查点/人工确认
  ├─ Tool Gateway：commerce/identity/MCP
  └─ PostgreSQL + pgvector + Redis + MinIO
```

### 14.2 兼容性提醒

当前项目是 Spring Boot 4.1.1。Spring AI 2.x 与 Boot 4 同代，但落地前必须做一次 **兼容性 spike**：

- Spring AI 版本与 Boot 4.1.1 的自动配置；
- MCP Client/Server starter 是否冲突；
- pgvector 方言与现有 Flyway；
- Java 21 运行时的模型 SDK 兼容性。

---

## 15. 分阶段落地路线

### Phase 0：技术验证（1–2 周）

- [ ] Spring AI + Boot 4.1.1 + LangGraph4j spike；
- [ ] 选 1 个 LLM Provider，跑通 ChatClient + 1 个只读工具；
- [ ] 建 `customerservice` schema 草案：session/message/agent_run/tool_call；
- [ ] 建 20 条 golden cases；
- [ ] 定义 `AgentTask/AgentResult` 契约。

验收：能完成“查订单状态”单轮只读任务，trace 可见。

### Phase 1：客服读链路 MVP（3–4 周）

- [ ] 意图识别 + 槽位追问；
- [ ] `OrderAgent` + `KnowledgeAgent`；
- [ ] RAG：售后政策/FAQ；
- [ ] SSE 流式；
- [ ] 引用、审计、转人工策略；
- [ ] 评测集 100 条。

验收：订单/物流/政策问题任务成功率 ≥ 80%，P95 首字 <2s，误转人工可解释。

### Phase 2：导购 + 写操作（3–4 周）

- [ ] `ShoppingGuideAgent`；
- [ ] 售后/地址写操作：确认 + 幂等 + 审计；
- [ ] `AfterSaleAgent` + 工单；
- [ ] 多 Agent 协同：退货 + 替代推荐；
- [ ] ChannelProfile（Web/H5/坐席）；
- [ ] 工具网关权限/限流/熔断。

验收：复杂任务可拆解执行；写操作 100% 有确认和审计；无越权。

### Phase 3：数据与模型优化（4–6 周）

- [ ] 会话/工具/反馈数据管道；
- [ ] 评测集 300+；
- [ ] SFT/LoRA 实验（意图/工具 JSON）；
- [ ] DPO 实验（语气/拒答）；
- [ ] 小模型路由/FAQ 蒸馏；
- [ ] 模型路由与成本看板。

验收：相对 prompt/RAG 基线，任务成功率或成本有可量化提升；无安全回退。

### Phase 4：内部 QA/Ops Agent（2–3 周）

- [ ] ZenTao MCP 工具：查/建 Bug、查用例；
- [ ] SkyWalking 工具：查 trace/慢 SQL；
- [ ] pytest/Allure 工具：失败用例归因；
- [ ] “发布风险摘要” Agent。

验收：能从失败用例生成“证据 + 归因 + 禅道 Bug 草稿”，人工确认后提交。

> 这条线可以独立于 C 端客服先做，风险低、复用现有资产，也最适合当前项目展示。

---

## 16. 风险与验收

| 风险 | 控制 |
|---|---|
| 多 Agent 过度设计 | 首期 1 Supervisor + 4–5 子 Agent；复杂任务再扩 |
| 模型幻觉/越权 | RAG 引用 + 工具网关 RBAC + 写确认 |
| 成本失控 | 模型路由、缓存、token 预算、max steps |
| 评测缺失 | 先建 golden set，再谈微调 |
| 多语言/多端分裂 | ChannelProfile + 统一 DTO |
| 微服务化过早 | 先在模块化单体落地，按 ADR 触发条件再拆 |
| 数据隐私 | 脱敏、最小化、审计、训练集隔离 |

### 面试可讲的验收指标

- 任务成功率；
- 工具调用准确率；
- P95 首字/全链路延迟；
- 转人工率/误转人工率；
- 单任务 token 成本；
- 写操作审计覆盖率；
- 评测回归通过率。

---

## 17. 面试表达建议

如果把这个项目讲给高德面试官，建议按“问题 → 架构 → 取舍 → 数据 → 结果”讲：

1. **问题**：电商客服跨订单/物流/售后/商品，单 Agent 工具太多、上下文太杂。
2. **架构**：Supervisor + 5 个子 Agent + Tool Gateway；MCP 管工具，内部接口管子 Agent；状态机和检查点保证可恢复。
3. **取舍**：不拆微服务、不做全自治 swarm；写操作必须确认；先 RAG/工具，后 SFT。
4. **数据**：会话/工具/反馈/评测集；SFT/DPO/蒸馏的触发条件。
5. **结果**：任务成功率、工具准确率、P95、转人工率、成本。
6. **边界**：明确哪些是设计、哪些已落地，不把规划说成上线。

---

## 18. 参考项目（GitHub）

> Star 数为 2026-11-05 查询，仅用于判断社区活跃度，不代表选型唯一依据。

| 项目 | 链接 | 参考点 |
|---|---|---|
| Spring AI | https://github.com/spring-projects/spring-ai | Java/Spring 的 ChatClient、Tool Calling、MCP、PGVector、Observability |
| LangChain4j | https://github.com/langchain4j/langchain4j | Java AI Services、工具、MCP、RAG |
| LangGraph4j | https://github.com/langgraph4j/langgraph4j | Java 状态图、检查点、人工介入 |
| LangGraph | https://github.com/langchain-ai/langgraph | Supervisor/子 Agent/状态图模式参考 |
| OpenAI Agents SDK | https://github.com/openai/openai-agents-python | handoff、guardrails、sessions、tracing 设计参考 |
| AutoGen | https://github.com/microsoft/autogen | 多 Agent 协作/群聊模式 |
| CrewAI | https://github.com/crewAIInc/crewAI | 角色/任务/流程抽象 |
| Google ADK | https://github.com/google/adk-python | 多 Agent、评测、部署工具链 |
| MCP Python SDK | https://github.com/modelcontextprotocol/python-sdk | 工具协议与 Server 实现参考 |
| A2A | https://github.com/a2aproject/A2A | Agent 间互操作协议 |
| Promptfoo | https://github.com/promptfoo/promptfoo | Prompt/Agent/RAG 评测与红队 |
| Ragas | https://github.com/explodinggradients/ragas | RAG 评测指标 |
| DeepEval | https://github.com/confident-ai/deepeval | LLM 评测框架 |
| Langfuse | https://github.com/langfuse/langfuse | LLM trace/评测/观测 |

---

## 19. 一句话总结

**用 Supervisor 管状态，用有边界的子 Agent 管领域，用 Tool Gateway 管权限与执行，用 RAG 管知识，用评测集管模型迭代；先跑通读链路和内部 QA Agent，再谈 SFT/DPO/蒸馏和多 Agent 自治。**
