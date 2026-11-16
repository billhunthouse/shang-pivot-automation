# 06 · 业务规则（As-built 摘要）

> 主源：`docs/06-baseline/02-业务规则与状态机.md`（基线 `810986c`）  
> 本页是给 LLM 检索的压缩版；精确行号/证据以主源为准。当前工作区新增的 C 端 AI 助手属于 `EXT-AI-001`，不改变以下 V1/V2 规则。

## 1. 订单状态机

状态值：`PENDING_PAY`（待付款）、`PENDING_SHIP`（待发货）、`PENDING_RECEIVE`（待收货）、`COMPLETED`（已完成）、`CLOSED`（已关闭）。

```text
POST /api/orders
  → PENDING_PAY（锁库存）
PENDING_PAY --支付成功--> PENDING_SHIP
PENDING_PAY --顾客取消/15分钟超时--> CLOSED（解锁）
PENDING_SHIP --后台发货--> PENDING_RECEIVE（扣 physical+locked）
PENDING_RECEIVE --确认收货--> COMPLETED
```

| ID | 转移 | 入口 | 守卫/副作用 |
|---|---|---|---|
| OT-01 | → `PENDING_PAY` | `POST /api/orders` | 顾客 NORMAL；`idempotentKey` 必填；地址/ SKU / SPU 校验；`SELECT ... FOR UPDATE` 锁库存；整单事务 |
| OT-02 | `PENDING_PAY` → `PENDING_SHIP` | `POST /api/payment/sandbox` | 沙箱开启；订单归属；状态必须是待付款；写 payment(PAID)、`paid_at`、`sold_count += qty` |
| OT-03 | `PENDING_PAY` → `CLOSED` | `POST /api/orders/{id}/cancel` | 归属；状态必须是待付款；`locked -= qty`（下限 0）；写 `UNLOCK`；已关闭重复取消幂等成功 |
| OT-04 | `PENDING_PAY` → `CLOSED` | 定时任务 `payTimeoutClose` | 默认 15 分钟；`LIMIT 100`；单条异常只 warn，不阻断其他单 |
| OT-05 | `PENDING_SHIP` → `PENDING_RECEIVE` | `POST /admin/orders/{id}/ship` | 状态必须待发货；`trackingNo` 必填；扣 physical+locked；写 `SHIP`；生成 `SALE_OUT` 出入库单 |
| OT-06 | `PENDING_RECEIVE` → `COMPLETED` | `POST /api/orders/{id}/confirm` | 归属；状态必须待收货 |
| OT-07 | `CLOSED` 重复取消 | 同 OT-03 | 直接返回，不二次释放库存/不写流水 |

**没有其他转移**：没有管理端取消/关单、没有超时自动确认收货、没有支付失败回退。

### 提交订单关键点

- 购物车路径（`cartItemIds` 优先）或立即购买（`quantity >= 1`）。
- 锁库存先于插订单；任一行失败整单回滚。
- `expireAt` 只用于响应，不落库。
- 订单号 `O + yyyyMMddHHmmss + %04d`，JVM `AtomicInteger`；同秒并发可能撞号，靠唯一索引兜底。
- 地址快照只存 name/phone/province/city/district/detail。
- 来自购物车的行会删除对应 `cart_item`。

## 2. 售后状态机

状态：`PENDING_AUDIT` → `REFUNDING` → `COMPLETED`；`PENDING_AUDIT` → `REJECTED`。

| ID | 规则 |
|---|---|
| AS-01 | `apply` 只要求登录，不校验 `isActive` |
| AS-02 | `type ∈ {REFUND, RETURN_REFUND, EXCHANGE}` |
| AS-03 | 订单必须存在且属于本人 |
| AS-04 | 只有 `PENDING_RECEIVE` / `COMPLETED` 可申请售后 |
| AS-05 | 同订单不能有进行中的售后（`PENDING_AUDIT`/`REFUNDING`） |
| AS-06 | 售后单号由时间戳 + 随机数生成，无唯一索引 |
| AS-07 | `refundAmount` 为空默认 `order.payAmount`；**无正数/上限校验** |
| AS-08 | 仅 `PENDING_AUDIT` 可审核 |
| AS-09 | 驳回必须填处理意见 |
| AS-10 | 通过时同一事务写 `REFUNDING` 再写 `COMPLETED`；`REFUNDING` 外部不可观测 |
| AS-11 | 三种 type 行为一致；`EXCHANGE` 也走退款流程；审核通过不退货入库、不退库存、不减销量、不写 payment |

**测试含义**：不要把“退款中”当成可观测状态；不要假设换货会换货；验证退款金额边界、并发重复审核、订单状态守卫。

## 3. 库存规则

不变式：

```text
physical_stock >= locked_stock >= 0
available = physical_stock - locked_stock（不落库）
```

| 操作 | stock_log.type | 变化 |
|---|---|---|
| 新建 SKU 初始库存 | `INIT` | `+qty`（仅 qty>0 写流水） |
| 后台手工调整 | `ADJUST` | 请求值（正入负出）；reason 固定“后台手工调整” |
| 下单锁库存 | `LOCK` | `+qty` |
| 关单释放 | `UNLOCK` | `-qty` |
| 发货出库 | `SHIP` | `-qty` |
| 采购入库/盘点 | `PURCHASE_IN` / `STOCKTAKE` | 按单据类型 |
| 发货 `SALE_OUT` | 不写 stock_log | 仅 in_out_order/in_out_item |

两级低库存：

- `lowOnly`：`available <= low_threshold`
- `warnOnly`：`available <= low_threshold * 1.5`（含低库存）
- 同时传 `lowOnly` 优先；默认阈值 10。

并发保护不一致：

- 下单/关单：`SELECT ... FOR UPDATE`。
- 发货/手工调整/手工出入库：普通 select + updateById，未检查影响行数；乐观锁冲突可能静默 0 行更新。

## 4. 商品与可见性

- C 端只展示 `spu.status = ON` 且 `deleted = false`；SKU 只展示 `status = ENABLED`。
- 上架校验：主图、至少 1 个 SKU、SKU 售价 > 0；库存为 0 允许上架。
- `sold_count` 在支付成功时按数量增加，取消/关单不回退（未支付路径不回退）。
- 商品详情：SPU + SKU 列表 + 每个 SKU 的可用库存 + 最近 5 条可见评价。

## 5. 认证与权限

- 管理端：`POST /admin/auth/login`，账号密码 + BCrypt；失败 5 次锁定 15 分钟（实现细节以代码为准）。
- C 端：`POST /api/auth/login` 手机号 + 验证码；演示环境固定码 `123456`，无真实短信。
- JWT：access TTL 900s，refresh TTL 7d；管理端与 C 端令牌不通用。
- 公开白名单以 `SecurityConfig` 为准：`/api/auth/**`、`/api/home`、`/api/site/brand`、`/api/products*`、`/api/categories`、`/api/search`、`/api/files/view`、`POST /api/customer-service/chat` 等。
- **后端 `/admin/**` 目前只认证不鉴权**（无 `@PreAuthorize` 命中），RBAC 主要影响前端菜单/按钮；这是演示级边界。

## 6. 支付、评价、购物车、地址

### 支付（沙箱）

- `POST /api/payment/sandbox {orderId}`：仅待付款、订单归属、顾客活跃、沙箱开关开启。
- 写 `payment(PAID)`、`paid_at`、`sold_count += qty`；**无真实资金、无回调、无对账**。

### 评价

- 仅已完成订单可评价；同一订单/商品不可重复评价。
- 评分 1–5；内容/图片需校验；当前实现存在 rating 缺失/越界返回 500 的缺口。
- 商家回复（V2.1 新增）：管理端 `PUT /admin/reviews/{id}/reply`，只写 `merchant_reply`/`replied_at`，不改星级、评价内容、可见性；1–500 字，空/超长返回 40000；C 端只展示 VISIBLE 评价的回复。

### 购物车

- 按 customer 唯一；条目按 skuId 合并；缺 skuId 拒绝；下单后清空选中项。
- 失效商品可清理；购物车项数无上限（NEG-S10）。

### 地址

- 一个顾客多地址；默认地址唯一；下单必须有效 `addressId`。
- 地址 id 为 19 位雪花号，前端必须字符串处理，`Number()` 会丢精度。
- 删除无守卫：可删默认地址/被订单引用地址（NEG-S09）。

## 7. 已知缺口/负面清单（生成测试时必须覆盖）

| 编号 | 缺口 | 测试含义 |
|---|---|---|
| NEG-S01 | 发货时 `order_item.skuId` 为空或 stock 缺失 → 静默跳过，库存不扣仍发货成功 | 构造缺失 stock / 空 skuId，断言不应成功 |
| NEG-S02 | 退款金额不校验 >0、不校验 <= payAmount | 负数/超额退款边界 |
| NEG-S05 | 编辑商品可直接把 status 写成任意值，绕过上架校验 | 无图/无 SKU/0 价直接 ON |
| NEG-S08 | 评价 rating 无代码校验，缺失 NPE→500、越界 DB CHECK→500 | 缺字段/0/6/负数应为 400 |
| NEG-S09 | 地址删除无守卫 | 删默认地址/被订单引用地址 |
| NEG-S10 | 分页/feedSize/购物车项数无上限 | 大 size、深分页、超大购物车 |
| NEG-S12 | 支付/发货/售后审核读-改-写且无行锁，可并发双通过 | 并发双支付/双发货/双审核 |
| NEG-S13 | initStock 可写负数 physical，DB CHECK 失败返回 500 | 负数初始库存应为 400 |
| NEG-S14 | 更新商品重建 SKU 时旧 stock 行不删，产生孤儿库存 | 更新 SKU 后检查 stock 行 |
| NEG-S18 | 商品可写不存在 categoryId/brandId（无外键/无校验） | 不存在类目/品牌 |
| NEG-S20 | 幂等键查后插无唯一冲突捕获，并发同 key 返回 500 | 同 key 并发下单 |
| NEG-S24 | `/admin/**` 只认证不鉴权 | 低权限管理员直接调管理接口 |
| NEG-S28 | 缺必填 query 参数返回 500 而非 400 | 缺参接口错误码 |
| NEG-S29 | 所有 `@RequestParam` 必填/路径类型不匹配都可能走 500 路径 | 参数类型/缺失矩阵 |

> 完整负面清单和证据见 `docs/06-baseline/02-业务规则与状态机.md` 第 10 节；不要把“PRD 写了”当成“代码已实现”。

## 8. 用例生成检查表

每个需求至少覆盖：

- 正常主流程 + 状态迁移前置/后置
- 未登录 / 冻结用户 / 非本人 / 越权
- 参数缺失、类型错误、边界值、超长/超大
- 重复提交、幂等键、并发请求
- 库存不足/锁定/释放/发货扣减
- 订单/售后非法状态
- 页面展示与接口状态一致性
- 审计日志/错误码/提示文案
