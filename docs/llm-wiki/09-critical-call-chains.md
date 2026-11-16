# 09 · 关键调用链（代码分析入口）

> 用于从“页面/接口/需求”快速下钻到 Controller → Service → 表。  
> 完整端点级链路见 `docs/06-baseline/05-调用链路.md`；本页只列最常用主链路。

## 1. 首页

```text
GET /api/home
→ StorefrontController.home
→ CatalogReadService.home
→ SiteBrandService / HomeSlotService
→ commerce.site_brand / home_slot / home_slot_item
→ 推荐流 toCard × N
→ commerce.spu / commerce.sku
   （toCard 每个 SPU 一次 sku 查询 = N+1）
```

## 2. 商品列表 / 搜索 / 详情

```text
GET /api/products
→ CatalogReadService.productPage
→ commerce.spu 分页
→ toCard × N → commerce.sku（每个 SPU 一次）

GET /api/search
→ CatalogReadService.search
→ commerce.spu（name/subtitle LIKE，前后通配）
→ toCard × N → commerce.sku

GET /api/products/{spuId}
→ CatalogReadService.detail
→ commerce.spu + commerce.sku
→ available(skuId) → commerce.stock（每个 SKU 一次）
→ commerce.review（最近 5 条）
```

## 3. 购物车

```text
GET /api/cart
→ CartService.getCart
→ commerce.cart + cart_item
→ toItemVo：每个条目查 sku / spu / stock（3 次/条）
```

## 4. 提交订单

```text
POST /api/orders
→ StorefrontController.submit
→ OrderSubmitService.submit
→ identity.customer（NORMAL）
→ commerce.address（归属校验）
→ commerce.sku / spu（上架/可售）
→ commerce.stock（SELECT ... FOR UPDATE，锁定库存）
→ commerce.order + order_item（快照）
→ commerce.stock_log（LOCK）
→ commerce.cart_item（删除选中项）
（整单本地事务；任一步失败回滚）
```

## 5. 沙箱支付

```text
POST /api/payment/sandbox
→ PaymentSandboxService.pay
→ commerce.order（归属 + PENDING_PAY）
→ commerce.payment（PAID）
→ commerce.order（paid_at）
→ commerce.spu（sold_count += qty）
```

## 6. 后台发货

```text
POST /admin/orders/{id}/ship
→ OrderService.ship
→ commerce.order（PENDING_SHIP）
→ commerce.shipment（SHIPPED + traces）
→ commerce.stock（physical -= qty, locked -= qty）
→ commerce.stock_log（SHIP）
→ commerce.in_out_order/item（SALE_OUT）
```

## 7. 售后申请 / 审核

```text
POST /api/after-sales
→ AfterSaleService.apply
→ commerce.order（归属 + PENDING_RECEIVE/COMPLETED）
→ commerce.after_sale（PENDING_AUDIT）
（不校验 isActive；不校验 refundAmount 上限）

POST /admin/after-sales/{id}/audit
→ AfterSaleService.audit
→ commerce.after_sale（PENDING_AUDIT）
→ 通过：REFUNDING → COMPLETED（同事务，外部不可观测）
→ 驳回：REJECTED（必须填意见）
（不退款、不退库存、不减销量、不写 payment）
```

## 8. C 端 AI 助手

```text
商城 AiAssistant.vue
→ POST /api/customer-service/chat
→ CustomerServiceController.chat
→ CustomerServiceAgentClient.chat
→ agent_service POST /agent/chat
→ LangGraph Supervisor / 子 Agent
   ├─ searchProducts → commerce /api/search|products
   ├─ getOrders → commerce /api/orders（透传商城 JWT）
   ├─ searchFaq → pgvector 知识库
   └─ after-sale 只到 need_confirmation
→ 返回 runId/traceId/status/answer；trace 另查 /agent/runs/{runId}
```

**注意**：AI 助手是独立的 `agent_service`（8088），不是 Java `shang-customerservice` 内部直接调 LLM；Java 层只做代理和 token 透传。

## 8.1 评价商家回复（V2.1）

```text
管理端评价管理
→ PUT /admin/reviews/{id}/reply
→ AdminOpsController.reviewReply
→ ReviewAdminService.reply（1–500 字校验、写 merchant_reply/replied_at）
→ commerce.review

商城商品详情
→ GET /api/products/{spuId}（reviewsPreview）
→ GET /api/products/{spuId}/reviews
→ 只返回 status=VISIBLE；有 merchant_reply 时展示
```

## 9. 鉴权前置

```text
管理端 /admin/**：
  JwtAuthFilter → SecurityFilterChain（authenticated）
  → 目前无 @PreAuthorize，接口级 RBAC 未落地

C 端 /api/**：
  JwtAuthFilter（可选）→ SecurityFilterChain
  → 公开白名单见 SecurityConfig
  → 受保护接口要求顾客 JWT

AI chat：
  POST /api/customer-service/chat 允许匿名
  → 若带 Authorization，透传给 agent_service 查订单
```
