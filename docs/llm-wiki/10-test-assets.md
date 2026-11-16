# 10 · 现有测试资产（复用与扩展）

> 新用例不是从零开始：优先复用现有契约用例、pytest、Cucumber UI 场景和 ZenTao 同步链路。

## 1. 契约 / API 用例

| 资产 | 位置 | 用途 |
|---|---|---|
| 端点模型 | `api_testcases/artifacts/endpoint-model.json` | 135 个端点的 DTO/字段/错误码/鉴权 |
| 调用图 | `api_testcases/artifacts/call-graph.json` | 端点 → Controller/Service/表 |
| 字段映射 | `api_testcases/artifacts/field-map.json` | 请求字段 → 实体/响应 |
| 用例清单 | `api_testcases/test_cases_inventory.md` | 424 契约 + 50 业务用例（基线） |
| 失败证据 | `api_testcases/artifacts/failures/` | JSON/PNG/steps 证据 |

生成新契约用例时：

1. 在 `endpoint-model.json` 找目标端点；
2. 用 `06-business-rules` 补状态/权限/库存约束；
3. 输出 `case_id`、method、path、headers、body、assertions、expected codes；
4. 跑 `pytest_automation`/`api_testcases` 验证，不直接写死真实订单号。

## 2. pytest 自动化 / 禅道同步

| 资产 | 位置 | 说明 |
|---|---|---|
| pytest 工程 | `pytest_automation/` | API/UI 自动化，845 条用例（历史基线） |
| 禅道同步 | `pytest_automation/core/zentao_sync.py` | 运行结果回写禅道，失败自动建 Bug + 附件 |
| 文档 | `pytest_automation/docs/禅道自动化同步.md` | 同步规则、套件、结果、Bug 证据 |
| 环境模板 | `pytest_automation/.env.example` | 本地/测试环境变量 |

新用例建议落到：

```text
pytest_automation/tests/...
```

并沿用现有 fixture/数据清理；不要引入真实支付、真实短信。

## 3. UI 场景

| 资产 | 位置 | 说明 |
|---|---|---|
| Cucumber 8 + Playwright | `ui_testcases/` | 5 个 feature、12 个场景（基线） |
| 前端页面 | `shang-mall` / `shang-admin-web` | 路由见 `04-page-map` |

新增 UI 场景时，从页面路由和 `04-page-map` 的 API 集合推导：

- 页面加载断言
- 空态/错误态/加载态
- 登录层/权限
- 关键操作后接口与页面状态一致
- 截图/录屏证据（失败时）

## 4. 性能与观测

| 资产 | 位置 | 用途 |
|---|---|---|
| k6 脚本 | `observability/k6/` | 浏览/登录/写链路 |
| 100 并发报告 | `docs/性能测试报告-k6-100并发-本地.md` | 当前性能基线 |
| 监控 | `observability/local/` | 本地 Prometheus/Grafana/DB exporter |
| SkyWalking/OTel | `observability/skywalking/` | 服务器链路追踪 |

## 5. 新用例生成的最小闭环

```text
需求（requirements.json）
  → 页面（pages.json）
  → 接口（apis.json）
  → 规则（06-business-rules）
  → 现有用例（api_testcases / pytest_automation / ui_testcases）
  → 新用例（JSONL / pytest）
  → 执行 + 证据 + 禅道同步
```

> 先用 `search`/grep 找现有相似用例，避免重复；新用例 ID 建议 `TC-<模块>-<序号>`，并保留 `requirement/api/page` 追溯字段。
