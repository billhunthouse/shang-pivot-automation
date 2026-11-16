# 代码地图

| Controller | 端点数 | Service | 表 |
|---|---:|---|---|
| AdminOpsController | 10 | HomeSlotService, InOutOrderService, ReviewAdminService, SiteBrandService | commerce.home_slot, commerce.home_slot_item, commerce.in_out_item, commerce.in_out_order, commerce.review, commerce.site_brand, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| AdminUserController | 7 | AdminUserService | identity.admin_user |
| AfterSaleController | 3 | AfterSaleService | commerce.after_sale, commerce.order |
| AttributeController | 4 | AttributeService | commerce.attribute |
| AuthController | 4 | AuthService | identity.admin_user |
| BrandController | 4 | BrandService | commerce.brand, commerce.category, commerce.spu |
| CategoryController | 5 | - | - |
| CustomerAdminController | 3 | CustomerAdminService | identity.customer |
| CustomerAuthController | 7 | CustomerAuthService | identity.customer |
| CustomerFileController | 4 | - | - |
| CustomerServiceController | 1 | CustomerServiceAgentClient | - |
| DashboardController | 1 | - | - |
| DeptController | 5 | - | - |
| DictController | 9 | - | - |
| FileController | 4 | - | - |
| OperationLogController | 3 | OperationLogService | identity.operation_log |
| OrderController | 4 | OrderService | commerce.order, commerce.order_item, commerce.payment, commerce.shipment, commerce.stock, commerce.stock_log |
| PermissionController | 5 | PermissionQueryService | identity.admin_role, identity.permission, identity.role, identity.role_permission |
| ProductController | 8 | ProductService | commerce.category, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| RoleController | 5 | RoleService | identity.role |
| StockController | 2 | StockService | commerce.sku, commerce.stock, commerce.stock_log, commerce.warehouse |
| StorefrontController | 34 | AddressService, AfterSaleService, CartService, CatalogReadService, FavoriteBrowseService, OrderSubmitService, PaymentSandboxService, SiteBrandService | commerce.address, commerce.after_sale, commerce.browse_history, commerce.cart, commerce.cart_item, commerce.category, commerce.favorite, commerce.order, commerce.order_item, commerce.payment, commerce.review, commerce.site_brand, commerce.sku, commerce.spu, commerce.stock, commerce.stock_log |
| SystemConfigController | 2 | - | - |
| WarehouseController | 3 | - | - |