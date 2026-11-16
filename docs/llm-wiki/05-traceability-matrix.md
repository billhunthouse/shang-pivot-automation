# 需求-页面-接口追溯矩阵

> 只列有页面落点的需求；接口为页面实际调用集合，不等同于需求全部接口。

| 需求 | 页面 | 接口数 | 代表接口 |
|---|---|---:|---|
| EXT-AI-001 商城 C 端 AI 助手浮窗（商品/知识/订单） | page:mall:ai-assistant | 1 | `POST /api/customer-service/chat` |
| EXT-REVIEW-REPLY-001 商品评价商家回复（管理端回复、C 端展示） | page:admin:/reviews, page:mall:/product/:spuId | 3 | `GET /admin/reviews`, `PUT /admin/reviews/{id}/reply`, `GET /api/products/{spuId}/reviews` |
| V1-FR-001 账密登录、失败锁定、登出 | page:admin:/login | 1 | `POST /admin/auth/login` |
| V1-FR-002 用户增删改查、启禁用、重置密码 | page:admin:/users | 8 | `DELETE /admin/users/{id}`, `GET /admin/depts/tree`, `GET /admin/roles/all`, `GET /admin/users`, `POST /admin/users` |
| V1-FR-003 角色、权限绑定、数据范围 | page:admin:/roles | 6 | `DELETE /admin/roles/{id}`, `GET /admin/permissions/tree`, `GET /admin/roles`, `GET /admin/users`, `POST /admin/roles` |
| V1-FR-004 权限树维护、侧栏与按钮权限 | page:admin:/menus | 5 | `DELETE /admin/permissions/{id}`, `GET /admin/permissions/tree`, `GET /admin/roles`, `POST /admin/permissions`, `PUT /admin/permissions/{id}` |
| V1-FR-005 部门树增删改查 | page:admin:/depts | 5 | `DELETE /admin/depts/{id}`, `GET /admin/depts/tree`, `GET /admin/users`, `POST /admin/depts`, `PUT /admin/depts/{id}` |
| V1-FR-006 字典类型与项 | page:admin:/dicts | 8 | `DELETE /admin/dict-items/{id}`, `DELETE /admin/dicts/{id}`, `GET /admin/dict-items`, `GET /admin/dicts`, `POST /admin/dict-items` |
| V1-FR-007 记录、查询、详情、导出 | page:admin:/logs | 3 | `GET /admin/operation-logs`, `GET /admin/operation-logs/export`, `GET /admin/operation-logs/{id}` |
| V1-FR-008 类目树增删改查 | page:admin:/categories | 13 | `DELETE /admin/attributes/{id}`, `DELETE /admin/brands/{id}`, `DELETE /admin/categories/{id}`, `GET /admin/attributes`, `GET /admin/brands` |
| V1-FR-009 品牌增删改查、归属类目 | page:admin:/categories | 13 | `DELETE /admin/attributes/{id}`, `DELETE /admin/brands/{id}`, `DELETE /admin/categories/{id}`, `GET /admin/attributes`, `GET /admin/brands` |
| V1-FR-010 属性、规格值维护 | page:admin:/categories | 13 | `DELETE /admin/attributes/{id}`, `DELETE /admin/brands/{id}`, `DELETE /admin/categories/{id}`, `GET /admin/attributes`, `GET /admin/brands` |
| V1-FR-011 SPU + 规格 + SKU 维护 | page:admin:/products/edit, page:admin:/products/edit/:id | 7 | `GET /admin/brands`, `GET /admin/categories/tree`, `GET /admin/products/{id}`, `POST /admin/files/upload`, `POST /admin/products` |
| V1-FR-012 查询、聚合展示 | page:admin:/products | 7 | `DELETE /admin/products/{id}`, `GET /admin/categories/tree`, `GET /admin/products`, `GET /admin/stocks`, `PUT /admin/products/batch-off` |
| V1-FR-013 上架校验、单个/批量下架、删除草稿 | page:admin:/products | 7 | `DELETE /admin/products/{id}`, `GET /admin/categories/tree`, `GET /admin/products`, `GET /admin/stocks`, `PUT /admin/products/batch-off` |
| V1-FR-014 图片上传与引用 | page:admin:/products/edit, page:admin:/products/edit/:id, page:admin:/site-brand | 9 | `GET /admin/brands`, `GET /admin/categories/tree`, `GET /admin/products/{id}`, `GET /admin/site/brand`, `POST /admin/files/upload` |
| V1-FR-015 三态查询、手动调整 | page:admin:/inventory | 2 | `GET /admin/stocks`, `PUT /admin/stocks/adjust` |
| V1-FR-016 阈值、低库存/关注两档、筛选 | page:admin:/inventory | 2 | `GET /admin/stocks`, `PUT /admin/stocks/adjust` |
| V1-FR-017 默认仓种子；无独立管理页 | page:admin:/inventory | 2 | `GET /admin/stocks`, `PUT /admin/stocks/adjust` |
| V1-FR-018 列表、详情 | page:admin:/orders | 4 | `GET /admin/orders`, `GET /admin/orders/export`, `GET /admin/orders/{id}`, `POST /admin/orders/{id}/ship` |
| V1-FR-019 承运商 + 运单号、状态流转 | page:admin:/orders | 4 | `GET /admin/orders`, `GET /admin/orders/export`, `GET /admin/orders/{id}`, `POST /admin/orders/{id}/ship` |
| V1-FR-020 列表、详情 | page:admin:/aftersales | 4 | `GET /admin/after-sales`, `GET /admin/after-sales/{id}`, `GET /admin/orders/{id}`, `POST /admin/after-sales/{id}/audit` |
| V1-FR-021 同意/拒绝 | page:admin:/aftersales | 4 | `GET /admin/after-sales`, `GET /admin/after-sales/{id}`, `GET /admin/orders/{id}`, `POST /admin/after-sales/{id}/audit` |
| V1-FR-022 配置 KV（分类 Tab、敏感脱敏） | page:admin:/settings | 2 | `GET /admin/system-configs`, `PUT /admin/system-configs/{id}` |
| V1-FR-023 统计摘要、低库存入口 | page:admin:/dashboard | 2 | `GET /admin/dashboard/stats`, `GET /admin/stocks` |
| V2-FR-001 手机号登录、游客浏览、登录引导、退出 | page:mall:/login, page:mall:/me, page:mall:/settings | 5 | `GET /api/me`, `POST /api/auth/login`, `POST /api/auth/logout`, `POST /api/auth/sms/send`, `PUT /api/me` |
| V2-FR-002 个人资料 | page:mall:/login, page:mall:/me, page:mall:/settings | 5 | `GET /api/me`, `POST /api/auth/login`, `POST /api/auth/logout`, `POST /api/auth/sms/send`, `PUT /api/me` |
| V2-FR-003 站点品牌、运营位、推荐流 | page:mall:/, page:mall:/promo/:code | 3 | `GET /api/categories`, `GET /api/home`, `GET /api/products` |
| V2-FR-004 分类导航与商品列表 | page:mall:/category, page:mall:/product/:spuId, page:mall:/search | 8 | `DELETE /api/favorites/{spuId}`, `GET /api/categories`, `GET /api/home`, `GET /api/products`, `GET /api/products/{spuId}` |
| V2-FR-005 搜索 | page:mall:/category, page:mall:/product/:spuId, page:mall:/search | 8 | `DELETE /api/favorites/{spuId}`, `GET /api/categories`, `GET /api/home`, `GET /api/products`, `GET /api/products/{spuId}` |
| V2-FR-006 商品详情与加购/购买 | page:mall:/product/:spuId | 4 | `DELETE /api/favorites/{spuId}`, `GET /api/products/{spuId}`, `POST /api/cart/items`, `POST /api/favorites/{spuId}` |
| V2-FR-007 增删改、勾选、失效、角标 | page:mall:/cart | 3 | `DELETE /api/cart/items/{id}`, `POST /api/cart/clear-invalid`, `PUT /api/cart/items/{id}` |
| V2-FR-008 确认订单 | page:mall:/checkout, page:mall:/pay/:orderId | 5 | `GET /api/addresses`, `GET /api/orders/{id}`, `GET /api/products/{spuId}`, `POST /api/orders`, `POST /api/payment/sandbox` |
| V2-FR-009 提交订单与待付款倒计时 | page:mall:/checkout, page:mall:/pay/:orderId | 5 | `GET /api/addresses`, `GET /api/orders/{id}`, `GET /api/products/{spuId}`, `POST /api/orders`, `POST /api/payment/sandbox` |
| V2-FR-010 模拟支付与结果页 | page:mall:/checkout, page:mall:/pay/:orderId | 5 | `GET /api/addresses`, `GET /api/orders/{id}`, `GET /api/products/{spuId}`, `POST /api/orders`, `POST /api/payment/sandbox` |
| V2-FR-011 列表、详情、取消、收货、物流 | page:mall:/orders, page:mall:/orders/:id | 7 | `GET /api/orders`, `GET /api/orders/{id}`, `GET /api/orders/{id}/logistics`, `POST /api/files/upload`, `POST /api/orders/{id}/cancel` |
| V2-FR-012 申请、列表、详情、凭证上传 | page:mall:/after-sales, page:mall:/after-sales/apply, page:mall:/after-sales/:id | 5 | `GET /api/after-sales`, `GET /api/after-sales/{id}`, `GET /api/orders/{id}`, `POST /api/after-sales`, `POST /api/files/upload` |
| V2-FR-013 首页、收藏、足迹、设置 | page:mall:/me, page:mall:/addresses, page:mall:/favorites, page:mall:/history | 9 | `DELETE /api/addresses/{id}`, `DELETE /api/favorites/{spuId}`, `DELETE /api/history`, `GET /api/addresses`, `GET /api/favorites` |
| V2-FR-014 地址管理 | page:mall:/me, page:mall:/addresses, page:mall:/favorites, page:mall:/history | 9 | `DELETE /api/addresses/{id}`, `DELETE /api/favorites/{spuId}`, `DELETE /api/history`, `GET /api/addresses`, `GET /api/favorites` |
| V2-FR-015 发表评价与详情页展示 | page:mall:/product/:spuId | 4 | `DELETE /api/favorites/{spuId}`, `GET /api/products/{spuId}`, `POST /api/cart/items`, `POST /api/favorites/{spuId}` |
| V2-FR-016 Web/H5 双布局 | page:mall:/, page:mall:/category, page:mall:/cart, page:mall:/me | 7 | `DELETE /api/cart/items/{id}`, `GET /api/categories`, `GET /api/home`, `GET /api/me`, `GET /api/products` |
| V2-FR-017 会员管理 | page:admin:/customers | 2 | `GET /admin/customers`, `PUT /admin/customers/{id}/status` |
| V2-FR-018 站点品牌 | page:admin:/site-brand | 3 | `GET /admin/site/brand`, `POST /admin/files/upload`, `PUT /admin/site/brand` |
| V2-FR-019 首页运营位 | page:admin:/home-slots | 4 | `GET /admin/home/slots`, `GET /admin/home/slots/{code}`, `GET /admin/products`, `PUT /admin/home/slots/{code}` |
| V2-FR-020 交易配置 | page:admin:/settings | 2 | `GET /admin/system-configs`, `PUT /admin/system-configs/{id}` |
| V2-FR-021 超时关单与销量回写 | page:admin:/orders | 4 | `GET /admin/orders`, `GET /admin/orders/export`, `GET /admin/orders/{id}`, `POST /admin/orders/{id}/ship` |
| V2-FR-022 订单增强与导出 | page:admin:/orders | 4 | `GET /admin/orders`, `GET /admin/orders/export`, `GET /admin/orders/{id}`, `POST /admin/orders/{id}/ship` |
| V2-FR-023 定时上架 | page:admin:/products/edit, page:admin:/products/edit/:id | 7 | `GET /admin/brands`, `GET /admin/categories/tree`, `GET /admin/products/{id}`, `POST /admin/files/upload`, `POST /admin/products` |
| V2-FR-024 出入库单 | page:admin:/in-out | 3 | `GET /admin/in-out`, `GET /admin/stocks`, `POST /admin/in-out` |
| V2-FR-025 评价管理 | page:admin:/reviews | 3 | `GET /admin/reviews`, `PUT /admin/reviews/{id}/reply`, `PUT /admin/reviews/{id}/status` |