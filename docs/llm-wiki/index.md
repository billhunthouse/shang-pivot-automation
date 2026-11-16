# LLM-wiki 导航

## 快速入口

| 你想做什么 | 先看 | 再用 |
|---|---|---|
| 先认术语 | [00-glossary.md](00-glossary.md) | `data/chunks.jsonl` |
| 理解项目全貌 | [01-overview.md](01-overview.md) | `data/graph.json` |
| 查需求有哪些 | [02-requirements.md](02-requirements.md) | `data/requirements.json` |
| 查接口定义/鉴权/服务/表 | [03-api-catalog.md](03-api-catalog.md) | `data/apis.json` |
| 查页面调用哪些接口 | [04-page-map.md](04-page-map.md) | `data/pages.json` |
| 做需求影响分析 | [05-traceability-matrix.md](05-traceability-matrix.md) | `08-llm-playbooks.md` |
| 查状态机/库存/鉴权/缺口 | [06-business-rules.md](06-business-rules.md) | `data/chunks.jsonl`（type=rule） |
| 查 Controller/Service/表 | [07-code-map.md](07-code-map.md) | `data/apis.json` |
| 让 LLM 生成用例 | [08-llm-playbooks.md](08-llm-playbooks.md) | `data/chunks.jsonl` |
| 让 LLM 做代码影响分析 | [08-llm-playbooks.md](08-llm-playbooks.md) | `data/graph.json` |
| 可视化知识图谱 | [graph.html](graph.html) | `data/knowledge-graph.json` / `graph.cypher` |
| 导入 Neo4j/Gephi | [graph.md](graph.md) | `data/graph.cypher` / `data/graph.graphml` |
| 查关键调用链 | [09-critical-call-chains.md](09-critical-call-chains.md) | `api_testcases/artifacts/call-graph.json` |
| 复用现有测试资产 | [10-test-assets.md](10-test-assets.md) | `api_testcases/`、`pytest_automation/` |
| 系统学习/带新人 | [course/README.md](course/README.md) | 13 节课 + 6 篇笔记（已接入 AI_Studio 学习中心） |

## 典型问题路由

| 问题 | 检索关键词 | 推荐 chunk |
|---|---|---|
| 新增优惠券要改哪里？ | 优惠券、订单、支付、购物车 | `type=requirement` + `type=rule` + `type=api` |
| 订单状态怎么流转？ | `PENDING_PAY`、`PENDING_SHIP` | `rule:order-state` |
| 退货为什么没有退款？ | 售后、REFUNDING、退款 | `rule:after-sale-state` + 06 负面清单 |
| 商品详情为什么查库存？ | `toCard`、`available`、stock | `api:GET:/api/products/{spuId}` + 07 |
| 哪些接口不需要登录？ | 免认证、SecurityConfig | `apis.json` 中 `public=true` |
| 管理端订单导出怎么测？ | `/admin/orders/export`、操作日志 | `api:GET:/admin/orders/export` |
| AI 助手在哪里？ | AI 助手、customer-service | `EXT-AI-001`、`api:POST:/api/customer-service/chat` |

## 目录结构

```text
01-overview.md              系统全景/模块/角色/端口
02-requirements.md          V1/V2/EXT 需求目录
03-api-catalog.md           136 个端点（按 tag）
04-page-map.md              C 端/管理端页面 → API
05-traceability-matrix.md   需求 → 页面 → 接口
06-business-rules.md        状态机/库存/鉴权/负面清单
07-code-map.md              Controller → Service → 表
08-llm-playbooks.md         需求分析/用例生成/代码分析模板
data/apis.json              机器可读 API
data/pages.json             机器可读页面
data/requirements.json      机器可读需求
data/graph.json             需求/页面/接口/服务/表图
data/chunks.jsonl           RAG 切片（239）
```

## 使用顺序建议

```text
先检索 requirements/pages/apis 确定范围
  → 用 graph.json 做一跳/两跳扩展
  → 用 06-business-rules 补充状态/库存/鉴权约束
  → 用 08-playbooks 生成分析或用例
  → 最后回代码/运行环境验证，不把 wiki 当唯一真值
```
