# 页面 ↔ API 映射

## C 端（shang-mall）

| 路由 | 页面 | 视图 | 调用接口 |
|---|---|---|---|
| `/login` | 登录 | `LoginView.vue` | `POST /api/auth/login`, `POST /api/auth/sms/send` |
| `/` | 首页 | `HomeView.vue` | `GET /api/categories`, `GET /api/home`, `GET /api/products` |
| `/promo/:code` | 活动专区 | `PromoView.vue` | `GET /api/home` |
| `/category` | 分类 | `CategoryView.vue` | `GET /api/categories`, `GET /api/products` |
| `/product/:spuId` | 商品详情 | `ProductView.vue` | `DELETE /api/favorites/{spuId}`, `GET /api/products/{spuId}`, `POST /api/cart/items`, `POST /api/favorites/{spuId}` |
| `/search` | 搜索 | `SearchView.vue` | `GET /api/home`, `GET /api/products`, `GET /api/search` |
| `/cart` | 购物车 | `CartView.vue` | `DELETE /api/cart/items/{id}`, `POST /api/cart/clear-invalid`, `PUT /api/cart/items/{id}` |
| `/checkout` | 确认订单 | `CheckoutView.vue` | `GET /api/addresses`, `GET /api/products/{spuId}`, `POST /api/orders` |
| `/orders` | 我的订单 | `OrdersView.vue` | `GET /api/orders` |
| `/orders/:id` | 订单详情 | `OrderDetailView.vue` | `GET /api/orders/{id}`, `GET /api/orders/{id}/logistics`, `POST /api/files/upload`, `POST /api/orders/{id}/cancel`, `POST /api/orders/{id}/confirm`, `POST /api/reviews` |
| `/pay/:orderId` | 支付 | `PayView.vue` | `GET /api/orders/{id}`, `POST /api/payment/sandbox` |
| `/me` | 个人中心 | `ProfileView.vue` | `GET /api/me` |
| `/settings` | 个人设置 | `SettingsView.vue` | `GET /api/me`, `POST /api/auth/logout`, `PUT /api/me` |
| `/addresses` | 收货地址 | `AddressView.vue` | `DELETE /api/addresses/{id}`, `GET /api/addresses`, `POST /api/addresses`, `PUT /api/addresses/{id}/default` |
| `/favorites` | 我的收藏 | `FavoritesView.vue` | `DELETE /api/favorites/{spuId}`, `GET /api/favorites` |
| `/history` | 浏览足迹 | `HistoryView.vue` | `DELETE /api/history`, `GET /api/history` |
| `/after-sales` | 我的售后 | `AfterSalesView.vue` | `GET /api/after-sales` |
| `/after-sales/apply` | 申请售后 | `AfterSaleApplyView.vue` | `GET /api/orders/{id}`, `POST /api/after-sales`, `POST /api/files/upload` |
| `/after-sales/:id` | 售后详情 | `AfterSaleDetailView.vue` | `GET /api/after-sales/{id}` |
| `(global)` | AI 助手浮窗 | `AiAssistant.vue` | `POST /api/customer-service/chat` |

## 管理端（shang-admin-web，部署前缀 `/admin`）

| 路由 | 页面 | 视图 | 调用接口 |
|---|---|---|---|
| `/admin/login` | 登录 | `LoginView.vue` | `POST /admin/auth/login` |
| `/admin/dashboard` | 工作台 | `DashboardView.vue` | `GET /admin/dashboard/stats`, `GET /admin/stocks` |
| `/admin/products` | 商品列表 | `ProductsView.vue` | `DELETE /admin/products/{id}`, `GET /admin/categories/tree`, `GET /admin/products`, `GET /admin/stocks`, `PUT /admin/products/batch-off`, `PUT /admin/products/{id}/off`, `PUT /admin/products/{id}/on` |
| `/admin/products/edit` | 新增商品 | `ProductEditView.vue` | `GET /admin/brands`, `GET /admin/categories/tree`, `GET /admin/products/{id}`, `POST /admin/files/upload`, `POST /admin/products`, `PUT /admin/products/{id}`, `PUT /admin/products/{id}/on` |
| `/admin/products/edit/:id` | 编辑商品 | `ProductEditView.vue` | `GET /admin/brands`, `GET /admin/categories/tree`, `GET /admin/products/{id}`, `POST /admin/files/upload`, `POST /admin/products`, `PUT /admin/products/{id}`, `PUT /admin/products/{id}/on` |
| `/admin/categories` | 类目与品牌 | `CategoriesView.vue` | `DELETE /admin/attributes/{id}`, `DELETE /admin/brands/{id}`, `DELETE /admin/categories/{id}`, `GET /admin/attributes`, `GET /admin/brands`, `GET /admin/categories/tree`, `GET /admin/products`, `POST /admin/attributes`, `POST /admin/brands`, `POST /admin/categories`, `PUT /admin/attributes/{id}`, `PUT /admin/brands/{id}`, `PUT /admin/categories/{id}` |
| `/admin/inventory` | 库存管理 | `InventoryView.vue` | `GET /admin/stocks`, `PUT /admin/stocks/adjust` |
| `/admin/in-out` | 出入库单 | `InOutView.vue` | `GET /admin/in-out`, `GET /admin/stocks`, `POST /admin/in-out` |
| `/admin/orders` | 订单列表 | `OrdersView.vue` | `GET /admin/orders`, `GET /admin/orders/export`, `GET /admin/orders/{id}`, `POST /admin/orders/{id}/ship` |
| `/admin/aftersales` | 售后管理 | `AftersalesView.vue` | `GET /admin/after-sales`, `GET /admin/after-sales/{id}`, `GET /admin/orders/{id}`, `POST /admin/after-sales/{id}/audit` |
| `/admin/reviews` | 评价管理 | `ReviewsView.vue` | `GET /admin/reviews`, `PUT /admin/reviews/{id}/reply`, `PUT /admin/reviews/{id}/status` |
| `/admin/customers` | 会员管理 | `CustomersView.vue` | `GET /admin/customers`, `PUT /admin/customers/{id}/status` |
| `/admin/site-brand` | 站点品牌 | `SiteBrandView.vue` | `GET /admin/site/brand`, `POST /admin/files/upload`, `PUT /admin/site/brand` |
| `/admin/home-slots` | 首页运营位 | `HomeSlotsView.vue` | `GET /admin/home/slots`, `GET /admin/home/slots/{code}`, `GET /admin/products`, `PUT /admin/home/slots/{code}` |
| `/admin/users` | 用户管理 | `UsersView.vue` | `DELETE /admin/users/{id}`, `GET /admin/depts/tree`, `GET /admin/roles/all`, `GET /admin/users`, `POST /admin/users`, `PUT /admin/users/{id}`, `PUT /admin/users/{id}/password`, `PUT /admin/users/{id}/status` |
| `/admin/roles` | 角色管理 | `RolesView.vue` | `DELETE /admin/roles/{id}`, `GET /admin/permissions/tree`, `GET /admin/roles`, `GET /admin/users`, `POST /admin/roles`, `PUT /admin/roles/{id}` |
| `/admin/menus` | 菜单与权限 | `MenusView.vue` | `DELETE /admin/permissions/{id}`, `GET /admin/permissions/tree`, `GET /admin/roles`, `POST /admin/permissions`, `PUT /admin/permissions/{id}` |
| `/admin/depts` | 部门管理 | `DeptsView.vue` | `DELETE /admin/depts/{id}`, `GET /admin/depts/tree`, `GET /admin/users`, `POST /admin/depts`, `PUT /admin/depts/{id}` |
| `/admin/dicts` | 字典管理 | `DictsView.vue` | `DELETE /admin/dict-items/{id}`, `DELETE /admin/dicts/{id}`, `GET /admin/dict-items`, `GET /admin/dicts`, `POST /admin/dict-items`, `POST /admin/dicts`, `PUT /admin/dict-items/{id}`, `PUT /admin/dicts/{id}` |
| `/admin/logs` | 操作日志 | `LogsView.vue` | `GET /admin/operation-logs`, `GET /admin/operation-logs/export`, `GET /admin/operation-logs/{id}` |
| `/admin/settings` | 系统设置 | `SettingsView.vue` | `GET /admin/system-configs`, `PUT /admin/system-configs/{id}` |