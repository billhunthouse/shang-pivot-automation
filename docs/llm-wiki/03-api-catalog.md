# API 目录（137 endpoints）

> 生成时间：2026-11-12 00:48；来源：`api_testcases/artifacts/call-graph.json` + `endpoint-model.json` + OpenAPI。

## C端AI助手

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| POST | `/api/customer-service/chat` | 商城 C 端 AI 助手对话（商品/知识/订单查询） | 免认证（可选会员 token 透传） | CustomerServiceController#chat / CustomerServiceAgentClient | - |

## C端商城

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/api/addresses` | 查询当前会员收货地址 | 会员 token | StorefrontController#addresses / AddressService | commerce.address |
| POST | `/api/addresses` | 新增收货地址 | 会员 token | StorefrontController#createAddress / AddressService | commerce.address |
| DELETE | `/api/addresses/{id}` | 删除收货地址 | 会员 token | StorefrontController#deleteAddress / AddressService | commerce.address |
| PUT | `/api/addresses/{id}` | 修改收货地址 | 会员 token | StorefrontController#updateAddress / AddressService | commerce.address |
| PUT | `/api/addresses/{id}/default` | 设置默认收货地址 | 会员 token | StorefrontController#defaultAddress / AddressService | commerce.address |
| GET | `/api/after-sales` | 查询当前会员售后单 | 会员 token | StorefrontController#myAfterSales / AfterSaleService | commerce.after_sale, commerce.order |
| POST | `/api/after-sales` | 申请售后 | 会员 token | StorefrontController#applyAfterSale / AfterSaleService | commerce.after_sale, commerce.order |
| GET | `/api/after-sales/{id}` | 查询售后详情 | 会员 token | StorefrontController#afterSaleDetail / AfterSaleService | commerce.after_sale, commerce.order |
| GET | `/api/cart` | 查询购物车 | 会员 token | StorefrontController#cart / CartService | commerce.cart, commerce.cart_item, commerce.sku, commerce.spu, commerce.stock |
| POST | `/api/cart/clear-invalid` | 清理失效购物车条目 | 会员 token | StorefrontController#clearInvalid / CartService | commerce.cart, commerce.cart_item, commerce.sku, commerce.spu, commerce.stock |
| POST | `/api/cart/items` | 加入购物车 | 会员 token | StorefrontController#addCart / CartService | commerce.cart, commerce.cart_item, commerce.sku, commerce.spu, commerce.stock |
| DELETE | `/api/cart/items/{id}` | 移除购物车条目 | 会员 token | StorefrontController#removeCart / CartService | commerce.cart, commerce.cart_item, commerce.sku, commerce.spu, commerce.stock |
| PUT | `/api/cart/items/{id}` | 修改购物车条目 | 会员 token | StorefrontController#updateCart / CartService | commerce.cart, commerce.cart_item, commerce.sku, commerce.spu, commerce.stock |
| GET | `/api/categories` | 查询类目树 | 免认证（GET） | StorefrontController#categories / CatalogReadService | commerce.category, commerce.review, commerce.sku, commerce.spu, commerce.stock |
| GET | `/api/favorites` | 查询收藏列表 | 会员 token | StorefrontController#favorites / FavoriteBrowseService | commerce.browse_history, commerce.favorite, commerce.spu |
| DELETE | `/api/favorites/{spuId}` | 取消收藏 | 会员 token | StorefrontController#removeFavorite / FavoriteBrowseService | commerce.browse_history, commerce.favorite, commerce.spu |
| POST | `/api/favorites/{spuId}` | 收藏商品 | 会员 token | StorefrontController#addFavorite / FavoriteBrowseService | commerce.browse_history, commerce.favorite, commerce.spu |
| DELETE | `/api/history` | 清空浏览足迹 | 会员 token | StorefrontController#clearHistory / FavoriteBrowseService | commerce.browse_history, commerce.favorite, commerce.spu |
| GET | `/api/history` | 查询浏览足迹 | 会员 token | StorefrontController#history / FavoriteBrowseService | commerce.browse_history, commerce.favorite, commerce.spu |
| GET | `/api/home` | 首页聚合（品牌、运营位、推荐流） | 免认证（GET） | StorefrontController#home / CatalogReadService | commerce.category, commerce.review, commerce.sku, commerce.spu, commerce.stock |
| GET | `/api/orders` | 查询当前会员订单 | 会员 token | StorefrontController#myOrders / - | - |
| POST | `/api/orders` | 提交订单 | 会员 token | StorefrontController#submit / OrderSubmitService | commerce.address, commerce.cart, commerce.cart_item, commerce.order, commerce.order_item, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| GET | `/api/orders/{id}` | 查询订单详情 | 会员 token | StorefrontController#orderDetail / - | - |
| POST | `/api/orders/{id}/cancel` | 取消订单 | 会员 token | StorefrontController#cancel / OrderSubmitService | commerce.address, commerce.cart, commerce.cart_item, commerce.order, commerce.order_item, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| POST | `/api/orders/{id}/confirm` | 确认收货 | 会员 token | StorefrontController#confirm / OrderSubmitService | commerce.address, commerce.cart, commerce.cart_item, commerce.order, commerce.order_item, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| GET | `/api/orders/{id}/logistics` | 查询订单物流 | 会员 token | StorefrontController#logistics / - | - |
| POST | `/api/payment/sandbox` | 沙箱支付 | 会员 token | StorefrontController#sandboxPay / PaymentSandboxService | commerce.order, commerce.order_item, commerce.payment, commerce.spu |
| GET | `/api/payment/{orderId}/status` | 查询支付状态 | 会员 token | StorefrontController#payStatus / PaymentSandboxService | commerce.order, commerce.order_item, commerce.payment, commerce.spu |
| GET | `/api/products` | 分页查询商品 | 免认证（GET） | StorefrontController#products / CatalogReadService | commerce.category, commerce.review, commerce.sku, commerce.spu, commerce.stock |
| GET | `/api/products/{spuId}` | 查询商品详情（SKU/库存） | 免认证（GET） | StorefrontController#productDetail / CatalogReadService, FavoriteBrowseService | commerce.browse_history, commerce.category, commerce.favorite, commerce.review, commerce.sku, commerce.spu, commerce.stock |
| GET | `/api/products/{spuId}/reviews` | 查询商品评价 | 免认证（GET） | StorefrontController#productReviews / - | - |
| POST | `/api/reviews` | 发表评价 | 会员 token | StorefrontController#createReview / - | - |
| GET | `/api/search` | 关键词搜索商品 | 免认证（GET） | StorefrontController#search / CatalogReadService | commerce.category, commerce.review, commerce.sku, commerce.spu, commerce.stock |
| GET | `/api/site/brand` | 查询站点品牌 | 免认证（GET） | StorefrontController#brand / SiteBrandService | commerce.site_brand |

## C端文件

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| POST | `/api/files/confirm` | 确认文件上传 | 会员 token | CustomerFileController#confirm / - | - |
| POST | `/api/files/presign` | 申请文件预签名上传 | 会员 token | CustomerFileController#presign / - | - |
| POST | `/api/files/upload` | 直传上传 | 会员 token | CustomerFileController#upload / - | - |
| GET | `/api/files/view` | 查看文件 | 免认证（GET） | CustomerFileController#view / - | - |

## V2运营补丁

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/home/slots` | 运营位列表 | 管理员 token | AdminOpsController#listSlots / HomeSlotService | commerce.home_slot, commerce.home_slot_item, commerce.sku, commerce.spu |
| GET | `/admin/home/slots/{code}` | 运营位详情 | 管理员 token | AdminOpsController#getSlot / HomeSlotService | commerce.home_slot, commerce.home_slot_item, commerce.sku, commerce.spu |
| PUT | `/admin/home/slots/{code}` | 保存运营位 | 管理员 token | AdminOpsController#saveSlot / HomeSlotService | commerce.home_slot, commerce.home_slot_item, commerce.sku, commerce.spu |
| GET | `/admin/in-out` | 出入库分页 | 管理员 token | AdminOpsController#inOutPage / InOutOrderService | commerce.in_out_item, commerce.in_out_order, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| POST | `/admin/in-out` | 创建出入库单 | 管理员 token | AdminOpsController#createInOut / InOutOrderService | commerce.in_out_item, commerce.in_out_order, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| GET | `/admin/reviews` | 评价分页 | 管理员 token | AdminOpsController#reviews / ReviewAdminService | commerce.review, commerce.spu |
| PUT | `/admin/reviews/{id}/status` | 隐藏/恢复评价 | 管理员 token | AdminOpsController#reviewStatus / ReviewAdminService | commerce.review, commerce.spu |
| GET | `/admin/site/brand` | 获取站点品牌 | 管理员 token | AdminOpsController#getBrand / SiteBrandService | commerce.site_brand |
| PUT | `/admin/site/brand` | 更新站点品牌 | 管理员 token | AdminOpsController#updateBrand / SiteBrandService | commerce.site_brand |

## 仓库管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/warehouses` | 获取仓库列表 | 管理员 token | WarehouseController#list / - | - |
| POST | `/admin/warehouses` | 创建仓库 | 管理员 token | WarehouseController#create / - | - |
| PUT | `/admin/warehouses/{id}` | 更新仓库 | 管理员 token | WarehouseController#update / - | - |

## 会员管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/customers` | 分页查询会员 | 管理员 token | CustomerAdminController#page / CustomerAdminService | identity.customer |
| GET | `/admin/customers/{id}` | 会员详情 | 管理员 token | CustomerAdminController#detail / CustomerAdminService | identity.customer |
| PUT | `/admin/customers/{id}/status` | 冻结/解冻会员 | 管理员 token | CustomerAdminController#updateStatus / CustomerAdminService | identity.customer |

## 品牌管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/brands` | 分页查询品牌 | 管理员 token | BrandController#page / BrandService | commerce.brand, commerce.category, commerce.spu |
| POST | `/admin/brands` | 创建品牌 | 管理员 token | BrandController#create / - | - |
| DELETE | `/admin/brands/{id}` | 删除品牌 | 管理员 token | BrandController#delete / - | - |
| PUT | `/admin/brands/{id}` | 更新品牌 | 管理员 token | BrandController#update / - | - |

## 售后管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/after-sales` | 分页查询售后单 | 管理员 token | AfterSaleController#page / AfterSaleService | commerce.after_sale, commerce.order |
| GET | `/admin/after-sales/{id}` | 获取售后详情 | 管理员 token | AfterSaleController#detail / AfterSaleService | commerce.after_sale, commerce.order |
| POST | `/admin/after-sales/{id}/audit` | 审核售后单 | 管理员 token | AfterSaleController#audit / AfterSaleService | commerce.after_sale, commerce.order |

## 商品管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/products` | 分页查询商品 | 管理员 token | ProductController#page / ProductService | commerce.category, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| POST | `/admin/products` | 创建商品 | 管理员 token | ProductController#create / ProductService | commerce.category, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| PUT | `/admin/products/batch-off` | 批量下架 | 管理员 token | ProductController#batchOff / ProductService | commerce.category, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| DELETE | `/admin/products/{id}` | 删除商品 | 管理员 token | ProductController#delete / ProductService | commerce.category, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| GET | `/admin/products/{id}` | 获取商品详情 | 管理员 token | ProductController#detail / ProductService | commerce.category, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| PUT | `/admin/products/{id}` | 更新商品 | 管理员 token | ProductController#update / ProductService | commerce.category, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| PUT | `/admin/products/{id}/off` | 商品下架 | 管理员 token | ProductController#off / ProductService | commerce.category, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| PUT | `/admin/products/{id}/on` | 商品上架 | 管理员 token | ProductController#on / ProductService | commerce.category, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |

## 字典管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/dict-items` | 查询字典项 | 管理员 token | DictController#items / - | - |
| POST | `/admin/dict-items` | 创建字典项 | 管理员 token | DictController#createItem / - | - |
| GET | `/admin/dict-items/by-code` | 按编码查询字典项 | 管理员 token | DictController#itemsByCode / - | - |
| DELETE | `/admin/dict-items/{id}` | 删除字典项 | 管理员 token | DictController#deleteItem / - | - |
| PUT | `/admin/dict-items/{id}` | 更新字典项 | 管理员 token | DictController#updateItem / - | - |
| GET | `/admin/dicts` | 分页查询字典 | 管理员 token | DictController#page / - | - |
| POST | `/admin/dicts` | 创建字典 | 管理员 token | DictController#createDict / - | - |
| DELETE | `/admin/dicts/{id}` | 删除字典 | 管理员 token | DictController#deleteDict / - | - |
| PUT | `/admin/dicts/{id}` | 更新字典 | 管理员 token | DictController#updateDict / - | - |

## 属性管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/attributes` | 查询属性列表 | 管理员 token | AttributeController#list / AttributeService | commerce.attribute |
| POST | `/admin/attributes` | 创建属性 | 管理员 token | AttributeController#create / - | - |
| DELETE | `/admin/attributes/{id}` | 删除属性 | 管理员 token | AttributeController#delete / - | - |
| PUT | `/admin/attributes/{id}` | 更新属性 | 管理员 token | AttributeController#update / - | - |

## 工作台

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/dashboard/stats` | 获取工作台统计 | 管理员 token | DashboardController#stats / - | - |

## 库存管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/stocks` | 分页查询库存 | 管理员 token | StockController#page / StockService | commerce.sku, commerce.stock, commerce.stock_log, commerce.warehouse |
| PUT | `/admin/stocks/adjust` | 调整库存 | 管理员 token | StockController#adjust / StockService | commerce.sku, commerce.stock, commerce.stock_log, commerce.warehouse |

## 操作日志

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/operation-logs` | 分页查询操作日志 | 管理员 token | OperationLogController#page / - | - |
| GET | `/admin/operation-logs/export` | 导出操作日志 | 管理员 token | OperationLogController#export / - | - |
| GET | `/admin/operation-logs/{id}` | 操作日志详情 | 管理员 token | OperationLogController#detail / OperationLogService | identity.operation_log |

## 文件上传

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| POST | `/admin/files/confirm` | 确认上传完成 | 管理员 token | FileController#confirm / - | - |
| POST | `/admin/files/presign` | 获取预签名上传地址 | 管理员 token | FileController#presign / - | - |
| POST | `/admin/files/upload` | 直传上传文件 | 管理员 token | FileController#upload / - | - |
| GET | `/admin/files/view` | 查看/下载文件 | 免认证（GET） | FileController#view / - | - |

## 用户管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/users` | 分页查询用户 | 管理员 token | AdminUserController#page / AdminUserService | identity.admin_user |
| POST | `/admin/users` | 创建用户 | 管理员 token | AdminUserController#create / AdminUserService | identity.admin_user |
| DELETE | `/admin/users/{id}` | 删除用户 | 管理员 token | AdminUserController#delete / AdminUserService | identity.admin_user |
| GET | `/admin/users/{id}` | 获取用户详情 | 管理员 token | AdminUserController#get / AdminUserService | identity.admin_user |
| PUT | `/admin/users/{id}` | 更新用户 | 管理员 token | AdminUserController#update / AdminUserService | identity.admin_user |
| PUT | `/admin/users/{id}/password` | 重置密码 | 管理员 token | AdminUserController#resetPassword / - | - |
| PUT | `/admin/users/{id}/status` | 更新用户状态 | 管理员 token | AdminUserController#status / - | - |

## 类目管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/categories` | 获取类目列表 | 管理员 token | CategoryController#list / - | - |
| POST | `/admin/categories` | 创建类目 | 管理员 token | CategoryController#create / - | - |
| GET | `/admin/categories/tree` | 获取类目树 | 管理员 token | CategoryController#tree / - | - |
| DELETE | `/admin/categories/{id}` | 删除类目 | 管理员 token | CategoryController#delete / - | - |
| PUT | `/admin/categories/{id}` | 更新类目 | 管理员 token | CategoryController#update / - | - |

## 系统配置

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/system-configs` | 查询系统配置 | 管理员 token | SystemConfigController#list / - | - |
| PUT | `/admin/system-configs/{id}` | 更新系统配置 | 管理员 token | SystemConfigController#update / - | - |

## 菜单权限

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/permissions` | 权限列表 | 管理员 token | PermissionController#list / - | - |
| POST | `/admin/permissions` | 创建权限 | 管理员 token | PermissionController#create / - | - |
| GET | `/admin/permissions/tree` | 权限树 | 管理员 token | PermissionController#tree / PermissionQueryService | identity.admin_role, identity.permission, identity.role, identity.role_permission |
| DELETE | `/admin/permissions/{id}` | 删除权限 | 管理员 token | PermissionController#delete / - | - |
| PUT | `/admin/permissions/{id}` | 更新权限 | 管理员 token | PermissionController#update / - | - |

## 角色管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/roles` | 分页查询角色 | 管理员 token | RoleController#page / RoleService | identity.role |
| POST | `/admin/roles` | 创建角色 | 管理员 token | RoleController#create / RoleService | identity.role |
| GET | `/admin/roles/all` | 查询全部角色 | 管理员 token | RoleController#all / RoleService | identity.role |
| DELETE | `/admin/roles/{id}` | 删除角色 | 管理员 token | RoleController#delete / RoleService | identity.role |
| PUT | `/admin/roles/{id}` | 更新角色 | 管理员 token | RoleController#update / RoleService | identity.role |

## 订单管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/orders` | 分页查询订单 | 管理员 token | OrderController#page / OrderService | commerce.order, commerce.order_item, commerce.payment, commerce.shipment, commerce.stock, commerce.stock_log |
| GET | `/admin/orders/export` | 导出订单 CSV | 管理员 token | OrderController#export / OrderService | commerce.order, commerce.order_item, commerce.payment, commerce.shipment, commerce.stock, commerce.stock_log |
| GET | `/admin/orders/{id}` | 获取订单详情 | 管理员 token | OrderController#detail / OrderService | commerce.order, commerce.order_item, commerce.payment, commerce.shipment, commerce.stock, commerce.stock_log |
| POST | `/admin/orders/{id}/ship` | 订单发货 | 管理员 token | OrderController#ship / OrderService | commerce.order, commerce.order_item, commerce.payment, commerce.shipment, commerce.stock, commerce.stock_log |

## 认证授权

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| POST | `/admin/auth/login` | 用户登录 | 免认证 | AuthController#login / AuthService | identity.admin_user |
| POST | `/admin/auth/logout` | 退出登录 | 管理员 token | AuthController#logout / AuthService | identity.admin_user |
| GET | `/admin/auth/me` | 获取当前用户信息 | 管理员 token | AuthController#me / AuthService | identity.admin_user |
| POST | `/admin/auth/refresh` | 刷新令牌 | 免认证 | AuthController#refresh / AuthService | identity.admin_user |

## 评价管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| PUT | `/admin/reviews/{id}/reply` | 回复评价（商家回复） | 管理员 token | AdminOpsController#reviewReply / ReviewAdminService | commerce.review |

## 部门管理

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| GET | `/admin/depts` | 部门列表 | 管理员 token | DeptController#list / - | - |
| POST | `/admin/depts` | 创建部门 | 管理员 token | DeptController#create / - | - |
| GET | `/admin/depts/tree` | 部门树 | 管理员 token | DeptController#tree / - | - |
| DELETE | `/admin/depts/{id}` | 删除部门 | 管理员 token | DeptController#delete / - | - |
| PUT | `/admin/depts/{id}` | 更新部门 | 管理员 token | DeptController#update / - | - |

## 顾客认证

| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |
|---|---|---|---|---|---|
| POST | `/api/auth/login` | 手机号验证码登录 | 免认证 | CustomerAuthController#login / CustomerAuthService | identity.customer |
| POST | `/api/auth/logout` | 退出登录 | 免认证 | CustomerAuthController#logout / CustomerAuthService | identity.customer |
| POST | `/api/auth/phone` | 手机号验证码登录 | 免认证 | CustomerAuthController#login / CustomerAuthService | identity.customer |
| POST | `/api/auth/refresh` | 刷新令牌 | 免认证 | CustomerAuthController#refresh / CustomerAuthService | identity.customer |
| POST | `/api/auth/sms/send` | 发送验证码 | 免认证 | CustomerAuthController#sendSms / CustomerAuthService | identity.customer |
| GET | `/api/me` | 当前顾客资料 | 会员 token | CustomerAuthController#me / CustomerAuthService | identity.customer |
| PUT | `/api/me` | 更新资料 | 会员 token | CustomerAuthController#updateMe / CustomerAuthService | identity.customer |
