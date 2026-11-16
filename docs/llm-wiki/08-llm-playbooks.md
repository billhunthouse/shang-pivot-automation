# 08 · LLM Playbooks

> 目标：让 LLM 基于本 wiki 做“新需求分析、用例生成、代码影响分析”，而不是泛泛而谈。  
> 原则：先检索、再扩展、再回代码验证；不要把 wiki 当唯一真值。

## 1. 通用检索流程

```text
Step 1 识别问题类型：requirement / page / api / rule / code
Step 2 选 chunk 类型：
  - 新需求 → requirement + rule
  - 页面问题 → page + api
  - 接口问题 → api + code-map
  - 状态/库存/权限 → rule
Step 3 检索 top-k（api 8；requirement/rule 5；page 5）
Step 4 用 links 做二跳：
  requirement → page → api
  api → controller/service/table
Step 5 回源码/运行环境验证：
  Controller 注解、Service 守卫、SecurityConfig、SQL、状态机
```

### 推荐检索查询

```text
"订单 状态 支付 发货 取消 库存"
"售后 退款 换货 REFUNDING 审核"
"商品详情 SKU 库存 评价"
"管理端 订单 导出 权限 审计"
"地址 默认 删除 订单 引用"
"AI 助手 customer-service chat"
```

### RAG 参数建议

| 场景 | top-k | 过滤 |
|---|---:|---|
| 需求影响 | 6 | `type in (requirement, rule)` |
| 接口定位 | 8 | `type=api` |
| 页面定位 | 5 | `type=page` |
| 用例生成 | 10 | requirement + page + api + rule |
| 代码分析 | 8 | api + rule |

## 2. Playbook A：新需求影响分析

### 输入

```text
需求描述：<一句话>
目标角色：游客/顾客/管理员
涉及端：C 端/管理端/两者
期望行为：<正常流程>
约束：<状态/权限/库存/支付/售后>
```

### 步骤

1. 检索最相近的 `requirement` 和 `rule`；
2. 在 `requirements.json` 找同模块需求，确认是否已有类似能力；
3. 通过 `pages.json` 找候选页面；
4. 通过 `apis.json` 找现有接口，判断“复用/扩展/新增”；
5. 通过 `graph.json` 找 Controller/Service/表；
6. 输出影响清单 + 风险 + 待确认问题。

### 输出模板

```markdown
## 需求理解
...

## 影响范围
| 层 | 影响项 | 复用/修改/新增 | 证据 |
|---|---|---|---|
| 页面 | ... | ... | page:... |
| 接口 | ... | ... | api:... |
| Controller/Service | ... | ... | 07-code-map |
| 表/字段 | ... | ... | 数据字典 |
| 状态机/规则 | ... | ... | rule:... |

## 风险
- 状态机...
- 权限...
- 库存/并发...
- 兼容/历史数据...

## 待确认
1. ...
```

### 禁止

- 不要凭 PRD 直接断言“已实现”；
- 不要忽略 `06-business-rules` 的负面清单；
- 不要把前端菜单权限当成后端鉴权。

## 3. Playbook B：测试用例生成

### 输入

```text
需求 ID / 需求描述：
页面路由：
接口：
优先级：P0/P1/P2
```

### 用例维度（至少）

| 维度 | 示例 |
|---|---|
| 正常流程 | 登录→加购→下单→支付 |
| 状态迁移 | 待付款→待发货；非法状态取消 |
| 权限 | 未登录、冻结、非本人、低权限管理员 |
| 参数 | 缺失、类型错误、边界、超长、特殊字符 |
| 幂等/并发 | 同 idempotentKey、双支付、双发货、双审核 |
| 库存 | 不足、锁定、释放、发货扣减、孤儿 stock |
| 页面/接口一致 | 页面展示 vs 接口状态 vs DB |
| 审计/错误码 | `@OpLog`、业务码、HTTP 状态 |

### 输出 JSONL 用例格式

```json
{"id":"TC-<模块>-001","requirement":"V2-FR-009","title":"提交订单-库存不足","priority":"P0","precondition":"已登录且地址有效","steps":["选择库存不足的SKU","提交订单"],"expected":{"http":409,"code":40901,"message":"库存不足","db":"订单不创建，库存不变"},"type":"negative"}
```

### 生成后自检

- 每条用例是否能追到需求/页面/接口/规则？
- 是否覆盖了负面清单中的对应缺口？
- 是否存在“只测 200、不测业务码”的假绿？
- 是否使用了雪花 ID 字符串而非 Number？
- 是否明确前置数据和清理策略？

## 4. Playbook C：代码影响分析

### 输入

```text
我要改：<类/方法/接口/字段>
```

### 步骤

1. 在 `apis.json` 按 `controller/method_name` 或 `path` 找端点；
2. 在 `graph.json` 走 `api → controller → service → table`；
3. 在 `07-code-map` 找同 Controller 的其他端点；
4. 检查 `06-business-rules` 中相关状态机/库存/权限约束；
5. 在 `requirements/pages` 找受影响需求/页面；
6. 输出影响面 + 回归范围 + 风险。

### 输出模板

```markdown
## 变更点
...

## 直接影响
- Controller:
- Service:
- Mapper/表:
- 端点:

## 间接受影响
- 需求:
- 页面:
- 其他端点:
- 测试:

## 风险
- 状态迁移:
- 库存/并发:
- 权限:
- 数据兼容:
```

## 5. Playbook D：缺陷定位（APP/前端/接口/DB）

```text
现象
  → 页面/路由（pages.json）
  → 请求接口（apis.json）
  → 业务码/HTTP
  → Controller/Service（graph.json）
  → SQL/表（tables）
  → 规则/状态机（06）
```

要求每个缺陷至少带：`traceId`、接口、请求参数、响应、用户/租户、时间、复现步骤、DB 证据。

## 6. 推荐系统提示词

```text
你是尚品汇项目的测试架构师。回答前必须先检索 docs/llm-wiki/data/chunks.jsonl：
1) 先找 requirement/rule，再找 page/api，最后找 code-map；
2) 每个结论必须给出 wiki chunk id 或源码路径；
3) 区分“PRD 宣称”“As-built 实现”“已知缺口”；
4) 不要编造接口、字段、状态；不确定就列为待确认；
5) 生成用例时覆盖正常/边界/异常/权限/状态/并发/幂等；
6) 输出结构化 Markdown 或 JSONL。
```
