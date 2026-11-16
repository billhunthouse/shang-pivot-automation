# 00 · 术语表

| 术语 | 含义 |
|---|---|
| SPU | 标准产品单元，商品聚合；`commerce.spu` |
| SKU | 最小库存/售卖单元；`commerce.sku`，一个 SPU 多个 SKU |
| 可用库存 | `physical_stock - locked_stock`，不落库 |
| 锁定库存 | 下单未支付时占用；取消/超时释放，发货扣减 |
| C 端 | 商城顾客端（`shang-mall`） |
| 管理端 | 后台运营端（`shang-admin-web`，部署前缀 `/admin`） |
| Customer | C 端顾客；`identity.customer` |
| AdminUser | 管理端用户；`identity.admin_user` |
| 租户/项目 | 本项目是单租户演示，前端仍传 `clientType`/项目上下文；不要套多租户假设 |
| ID 雪花号 | 19 位 Long；前端必须用字符串，`Number()` 会丢精度 |
| `PENDING_PAY` | 待付款 |
| `PENDING_SHIP` | 待发货（已支付） |
| `PENDING_RECEIVE` | 待收货（已发货） |
| `COMPLETED` | 已完成 |
| `CLOSED` | 已关闭（取消/超时） |
| `PENDING_AUDIT` | 售后待审核 |
| `REFUNDING` | 售后退款中（实现中瞬态，外部不可观测） |
| `REJECTED` | 售后已拒绝 |
| `idempotentKey` | 下单幂等键；同一顾客唯一 |
| `@OpLog` | 管理端操作审计注解；C 端无审计 |
| As-built | 按实际代码反推的实现事实，不等于 PRD |
| NEG-Sxx | 负面清单/已知缺口编号，见 `06-business-rules` |
