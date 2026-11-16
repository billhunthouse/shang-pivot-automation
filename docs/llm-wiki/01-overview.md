# 01 · 系统全景

## 1. 项目定位

尚品汇（Shang Pivot）是一个**分版本演进的电商全栈演示项目**：

```text
V1.0 后台管理（商品/库存/订单/售后/权限）
  ↓
V2.0 C 端交易（商城 Web + H5）
  ↓
V3.0 智能客服（C 端 AI 助手已接入；人工坐席/工单未实现）
```

- 后端：Java 21 / Spring Boot 4.1.1 / MyBatis-Plus / PostgreSQL 16 / Redis 7 / Flyway
- 前端：Vue 3 + Vite
  - 商城 C 端：Vant，`shang-mall/`
  - 管理端：Element Plus，`shang-admin-web/`
- 架构：模块化单体，`shang-server` 聚合启动，模块之间只通过 `*-api` 契约交互
- Agent：独立 Python `agent_service/`（LangGraph + FastAPI），商城通过 `shang-customerservice` 代理接入

## 2. 运行拓扑

```text
Browser
  ├── shang-mall (Vite 5174) ──/api──┐
  └── shang-admin-web (Vite 5173) ──/admin──┐
                                           ▼
                                  shang-server 8086
                                  ├── identity 上下文
                                  ├── commerce 上下文
                                  └── customerservice 上下文
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              PostgreSQL             Redis              agent_service 8088
              (55434, pgvector)      (56379)            (LangGraph/FastAPI)
```

> 端口是本地约定：后端 8086，Actuator 8087（仅回环），商城 5174，管理端 5173。

## 3. 模块边界

| Maven 模块 | 职责 | 主要代码 |
|---|---|---|
| `shang-common` | Result/异常/JWT/Redis/OSS/审计/过滤器 | `backend/shang-common` |
| `shang-identity-api` | 身份对外契约 | `CustomerQueryApi`、`SystemConfigApi` |
| `shang-identity` | 管理员/顾客认证、RBAC、菜单、部门、字典、文件、日志、配置 | `backend/shang-identity` |
| `shang-commerce-api` | 交易对外契约 | `OrderQueryApi`、`StockApi`（空接口） |
| `shang-commerce` | 类目/品牌/属性/SPU/SKU/库存/订单/支付/售后/评价/运营位 | `backend/shang-commerce` |
| `shang-customerservice` | C 端 AI 助手代理（旧基线为占位） | `backend/shang-customerservice` |
| `shang-server` | 聚合启动 + Flyway + 配置 | `backend/shang-server` |
| `agent_service` | Phase-0 LangGraph Agent 服务 | `agent_service/` |

**硬约束**：`shang-identity` 和 `shang-commerce` 的实现模块不能互相直接依赖；跨上下文只走 `*-api`。

## 4. 角色与入口

| 角色 | 入口 | 能力 |
|---|---|---|
| 游客 | 商城 C 端 | 浏览首页/分类/搜索/详情；购物车可看，结算登录 |
| 顾客 | 商城 C 端 `/login` | 下单、支付、订单、售后、地址、收藏、足迹、评价、AI 助手 |
| 管理员 | 管理端 `/login` | 商品/库存/订单/售后/会员/运营/权限/日志/设置 |
| 开发者/评审者/只读 | 管理端（按权限） | 管理端权限目前主要影响前端菜单/按钮；后端接口级鉴权仍是演示级 |
| AI 助手 | 商城右下角浮窗 | 商品推荐、知识问答、订单查询；未登录订单返回 `need_auth` |

## 5. 页面域

### C 端（`shang-mall`）

- 浏览：`/`、`/promo/:code`、`/category`、`/search`、`/product/:spuId`
- 交易：`/cart`、`/checkout`、`/pay/:orderId`
- 订单/售后：`/orders`、`/orders/:id`、`/after-sales*`
- 会员：`/login`、`/me`、`/settings`、`/addresses`、`/favorites`、`/history`
- 全局浮窗：AI 助手（所有 C 端页面）

### 管理端（`shang-admin-web`，部署前缀 `/admin`）

- 概览：`/dashboard`
- 商品：`/products`、`/products/edit`、`/categories`、`/inventory`、`/in-out`
- 交易：`/orders`、`/aftersales`、`/reviews`、`/customers`
- 内容：`/site-brand`、`/home-slots`
- 系统：`/users`、`/roles`、`/menus`、`/depts`、`/dicts`、`/logs`、`/settings`

## 6. 核心数据域

| Schema | 表数 | 核心表 |
|---|---:|---|
| `identity` | 12 | `customer`、`admin_user`、`role`、`permission`、`role_permission`、`admin_role`、`dept`、`dict`、`dict_item`、`system_config`、`file_object`、`operation_log` |
| `commerce` | 24 | `category`、`brand`、`attribute`、`spu`、`sku`、`warehouse`、`stock`、`stock_log`、`order`、`order_item`、`payment`、`shipment`、`after_sale`、`cart`、`cart_item`、`address`、`favorite`、`browse_history`、`review`、`site_brand`、`home_slot`、`home_slot_item`、`in_out_order`、`in_out_item` |

完整字段：`docs/06-baseline/01-数据字典.md`；字段映射：`04-字段映射.md`。

## 7. 真值顺序（做分析前必读）

1. **运行代码**：Controller / Service / SecurityConfig / Mapper / SQL
2. **As-built 规则**：`docs/06-baseline/02-业务规则与状态机.md`（基线 `810986c`）
3. **生成物**：`call-graph.json` / `endpoint-model.json` / OpenAPI（有快照时间）
4. **PRD**：`docs/01-requirements/PRD-V1.0`、`PRD-V2.0`（需求意图）
5. **本 wiki**：导航和自动映射，不能替代代码验证

> 旧基线说“AI 智能客服为空占位”，但当前工作区已新增 C 端 AI 助手，作为 `EXT-AI-001` 记录；旧基线仍是 V1/V2 业务规则的主要真值。
