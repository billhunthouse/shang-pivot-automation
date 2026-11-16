"""41 个页面的 UI 冒烟目录。

page_id 与 docs/llm-wiki/data/pages.json 对齐，供覆盖率脚本统计。
checkout / pay 由核心交易链路覆盖，不放在纯页面冒烟里。
"""
from __future__ import annotations

PAGE_CATALOG: list[dict[str, str]] = [
    # ---------------- 商城 C 端 ----------------
    {"page_id": "page:mall:/login", "area": "mall", "role": "guest", "path": "/login", "expect": "登录尚品汇", "case_id": "UI-PAGE-MALL-001", "title": "登录页"},
    {"page_id": "page:mall:/", "area": "mall", "role": "guest", "path": "/", "expect": "热门精选 SPU", "case_id": "UI-PAGE-MALL-002", "title": "首页"},
    {"page_id": "page:mall:/promo/:code", "area": "mall", "role": "guest", "path": "/promo/home_promo_subsidy", "expect": "活动位 · 热门精选", "case_id": "UI-PAGE-MALL-003", "title": "活动专区"},
    {"page_id": "page:mall:/category", "area": "mall", "role": "guest", "path": "/category", "expect": "分类", "case_id": "UI-PAGE-MALL-004", "title": "分类页"},
    {"page_id": "page:mall:/product/:spuId", "area": "mall", "role": "guest", "path": "/product/111", "expect": "vivo X100", "case_id": "UI-PAGE-MALL-005", "title": "商品详情"},
    {"page_id": "page:mall:/search", "area": "mall", "role": "guest", "path": "/search?q=iPhone", "expect": "搜索", "case_id": "UI-PAGE-MALL-006", "title": "搜索页"},
    {"page_id": "page:mall:/cart", "area": "mall", "role": "guest", "path": "/cart", "expect": "购物车", "case_id": "UI-PAGE-MALL-007", "title": "购物车"},
    {"page_id": "page:mall:/orders", "area": "mall", "role": "customer", "path": "/orders", "expect": "我的订单", "case_id": "UI-PAGE-MALL-008", "title": "我的订单"},
    {"page_id": "page:mall:/orders/:id", "area": "mall", "role": "customer", "path": "/orders/104", "expect": "订单详情", "case_id": "UI-PAGE-MALL-009", "title": "订单详情"},
    {"page_id": "page:mall:/me", "area": "mall", "role": "customer", "path": "/me", "expect": "我的", "case_id": "UI-PAGE-MALL-010", "title": "个人中心"},
    {"page_id": "page:mall:/settings", "area": "mall", "role": "customer", "path": "/settings", "expect": "设置", "case_id": "UI-PAGE-MALL-011", "title": "个人设置"},
    {"page_id": "page:mall:/addresses", "area": "mall", "role": "customer", "path": "/addresses", "expect": "收货地址", "case_id": "UI-PAGE-MALL-012", "title": "收货地址"},
    {"page_id": "page:mall:/favorites", "area": "mall", "role": "customer", "path": "/favorites", "expect": "我的收藏", "case_id": "UI-PAGE-MALL-013", "title": "我的收藏"},
    {"page_id": "page:mall:/history", "area": "mall", "role": "customer", "path": "/history", "expect": "浏览足迹", "case_id": "UI-PAGE-MALL-014", "title": "浏览足迹"},
    {"page_id": "page:mall:/after-sales", "area": "mall", "role": "customer", "path": "/after-sales", "expect": "我的售后", "case_id": "UI-PAGE-MALL-015", "title": "我的售后"},
    {"page_id": "page:mall:/after-sales/apply", "area": "mall", "role": "customer", "path": "/after-sales/apply?orderId=104", "expect": "申请售后", "case_id": "UI-PAGE-MALL-016", "title": "申请售后"},
    {"page_id": "page:mall:/after-sales/:id", "area": "mall", "role": "customer", "path": "/after-sales/101", "expect": "售后详情", "case_id": "UI-PAGE-MALL-017", "title": "售后详情"},
    {"page_id": "page:mall:ai-assistant", "area": "mall", "role": "guest", "path": "/", "expect": "尚品汇 AI 助手", "case_id": "UI-PAGE-MALL-018", "title": "AI 助手浮窗", "special": "ai"},
    # ---------------- 管理端 ----------------
    {"page_id": "page:admin:/login", "area": "admin", "role": "guest", "path": "/login", "expect": "Shang 商城后台", "case_id": "UI-PAGE-ADMIN-001", "title": "管理端登录"},
    {"page_id": "page:admin:/dashboard", "area": "admin", "role": "admin", "path": "/dashboard", "expect": "Phase 1 供给侧工作台", "case_id": "UI-PAGE-ADMIN-002", "title": "工作台"},
    {"page_id": "page:admin:/products", "area": "admin", "role": "admin", "path": "/products", "expect": "商品列表", "case_id": "UI-PAGE-ADMIN-003", "title": "商品列表"},
    {"page_id": "page:admin:/products/edit", "area": "admin", "role": "admin", "path": "/products/edit", "expect": "新增商品", "case_id": "UI-PAGE-ADMIN-004", "title": "新增商品"},
    {"page_id": "page:admin:/products/edit/:id", "area": "admin", "role": "admin", "path": "/products/edit/111", "expect": "编辑商品", "case_id": "UI-PAGE-ADMIN-005", "title": "编辑商品"},
    {"page_id": "page:admin:/categories", "area": "admin", "role": "admin", "path": "/categories", "expect": "类目与品牌", "case_id": "UI-PAGE-ADMIN-006", "title": "类目与品牌"},
    {"page_id": "page:admin:/inventory", "area": "admin", "role": "admin", "path": "/inventory", "expect": "库存管理", "case_id": "UI-PAGE-ADMIN-007", "title": "库存管理"},
    {"page_id": "page:admin:/in-out", "area": "admin", "role": "admin", "path": "/in-out", "expect": "出入库单", "case_id": "UI-PAGE-ADMIN-008", "title": "出入库单"},
    {"page_id": "page:admin:/orders", "area": "admin", "role": "admin", "path": "/orders", "expect": "订单列表", "case_id": "UI-PAGE-ADMIN-009", "title": "订单列表"},
    {"page_id": "page:admin:/aftersales", "area": "admin", "role": "admin", "path": "/aftersales", "expect": "售后管理", "case_id": "UI-PAGE-ADMIN-010", "title": "售后管理"},
    {"page_id": "page:admin:/reviews", "area": "admin", "role": "admin", "path": "/reviews", "expect": "评价管理", "case_id": "UI-PAGE-ADMIN-011", "title": "评价管理"},
    {"page_id": "page:admin:/customers", "area": "admin", "role": "admin", "path": "/customers", "expect": "会员管理", "case_id": "UI-PAGE-ADMIN-012", "title": "会员管理"},
    {"page_id": "page:admin:/site-brand", "area": "admin", "role": "admin", "path": "/site-brand", "expect": "站点品牌", "case_id": "UI-PAGE-ADMIN-013", "title": "站点品牌"},
    {"page_id": "page:admin:/home-slots", "area": "admin", "role": "admin", "path": "/home-slots", "expect": "首页运营位", "case_id": "UI-PAGE-ADMIN-014", "title": "首页运营位"},
    {"page_id": "page:admin:/users", "area": "admin", "role": "admin", "path": "/users", "expect": "用户管理", "case_id": "UI-PAGE-ADMIN-015", "title": "用户管理"},
    {"page_id": "page:admin:/roles", "area": "admin", "role": "admin", "path": "/roles", "expect": "角色管理", "case_id": "UI-PAGE-ADMIN-016", "title": "角色管理"},
    {"page_id": "page:admin:/menus", "area": "admin", "role": "admin", "path": "/menus", "expect": "菜单与权限", "case_id": "UI-PAGE-ADMIN-017", "title": "菜单与权限"},
    {"page_id": "page:admin:/depts", "area": "admin", "role": "admin", "path": "/depts", "expect": "部门管理", "case_id": "UI-PAGE-ADMIN-018", "title": "部门管理"},
    {"page_id": "page:admin:/dicts", "area": "admin", "role": "admin", "path": "/dicts", "expect": "字典管理", "case_id": "UI-PAGE-ADMIN-019", "title": "字典管理"},
    {"page_id": "page:admin:/logs", "area": "admin", "role": "admin", "path": "/logs", "expect": "操作日志", "case_id": "UI-PAGE-ADMIN-020", "title": "操作日志"},
    {"page_id": "page:admin:/settings", "area": "admin", "role": "admin", "path": "/settings", "expect": "系统设置", "case_id": "UI-PAGE-ADMIN-021", "title": "系统设置"},
]
