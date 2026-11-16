#!/usr/bin/env python3
"""Build the ShangPivot LLM wiki from OpenAPI, call graph, routes and PRDs.

Usage: python3 docs/llm-wiki/scripts/build_wiki.py
Outputs: docs/llm-wiki/data/*.json, chunks.jsonl and generated catalog pages.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WIKI = ROOT / "docs" / "llm-wiki"
DATA = WIKI / "data"
CALL_GRAPH = ROOT / "api_testcases" / "artifacts" / "call-graph.json"
ENDPOINT_MODEL = ROOT / "api_testcases" / "artifacts" / "endpoint-model.json"
OPENAPI = ROOT / "docs" / "openapi-v3-api-docs.json"

MALL_PAGES = [
    ("/login", "登录", "shang-mall/src/views/LoginView.vue"),
    ("/", "首页", "shang-mall/src/views/HomeView.vue"),
    ("/promo/:code", "活动专区", "shang-mall/src/views/PromoView.vue"),
    ("/category", "分类", "shang-mall/src/views/CategoryView.vue"),
    ("/product/:spuId", "商品详情", "shang-mall/src/views/ProductView.vue"),
    ("/search", "搜索", "shang-mall/src/views/SearchView.vue"),
    ("/cart", "购物车", "shang-mall/src/views/CartView.vue"),
    ("/checkout", "确认订单", "shang-mall/src/views/CheckoutView.vue"),
    ("/orders", "我的订单", "shang-mall/src/views/OrdersView.vue"),
    ("/orders/:id", "订单详情", "shang-mall/src/views/OrderDetailView.vue"),
    ("/pay/:orderId", "支付", "shang-mall/src/views/PayView.vue"),
    ("/me", "个人中心", "shang-mall/src/views/ProfileView.vue"),
    ("/settings", "个人设置", "shang-mall/src/views/SettingsView.vue"),
    ("/addresses", "收货地址", "shang-mall/src/views/AddressView.vue"),
    ("/favorites", "我的收藏", "shang-mall/src/views/FavoritesView.vue"),
    ("/history", "浏览足迹", "shang-mall/src/views/HistoryView.vue"),
    ("/after-sales", "我的售后", "shang-mall/src/views/AfterSalesView.vue"),
    ("/after-sales/apply", "申请售后", "shang-mall/src/views/AfterSaleApplyView.vue"),
    ("/after-sales/:id", "售后详情", "shang-mall/src/views/AfterSaleDetailView.vue"),
]

ADMIN_PAGES = [
    ("/login", "登录", "shang-admin-web/src/views/LoginView.vue"),
    ("/dashboard", "工作台", "shang-admin-web/src/views/DashboardView.vue"),
    ("/products", "商品列表", "shang-admin-web/src/views/ProductsView.vue"),
    ("/products/edit", "新增商品", "shang-admin-web/src/views/ProductEditView.vue"),
    ("/products/edit/:id", "编辑商品", "shang-admin-web/src/views/ProductEditView.vue"),
    ("/categories", "类目与品牌", "shang-admin-web/src/views/CategoriesView.vue"),
    ("/inventory", "库存管理", "shang-admin-web/src/views/InventoryView.vue"),
    ("/in-out", "出入库单", "shang-admin-web/src/views/InOutView.vue"),
    ("/orders", "订单列表", "shang-admin-web/src/views/OrdersView.vue"),
    ("/aftersales", "售后管理", "shang-admin-web/src/views/AftersalesView.vue"),
    ("/reviews", "评价管理", "shang-admin-web/src/views/ReviewsView.vue"),
    ("/customers", "会员管理", "shang-admin-web/src/views/CustomersView.vue"),
    ("/site-brand", "站点品牌", "shang-admin-web/src/views/SiteBrandView.vue"),
    ("/home-slots", "首页运营位", "shang-admin-web/src/views/HomeSlotsView.vue"),
    ("/users", "用户管理", "shang-admin-web/src/views/UsersView.vue"),
    ("/roles", "角色管理", "shang-admin-web/src/views/RolesView.vue"),
    ("/menus", "菜单与权限", "shang-admin-web/src/views/MenusView.vue"),
    ("/depts", "部门管理", "shang-admin-web/src/views/DeptsView.vue"),
    ("/dicts", "字典管理", "shang-admin-web/src/views/DictsView.vue"),
    ("/logs", "操作日志", "shang-admin-web/src/views/LogsView.vue"),
    ("/settings", "系统设置", "shang-admin-web/src/views/SettingsView.vue"),
]

V1_MODULE_PAGES = {
    "登录": ["/login"],
    "用户管理": ["/users"],
    "角色管理": ["/roles"],
    "菜单与权限": ["/menus"],
    "部门管理": ["/depts"],
    "字典管理": ["/dicts"],
    "操作日志": ["/logs"],
    "类目管理": ["/categories"],
    "品牌管理": ["/categories"],
    "属性管理": ["/categories"],
    "商品编辑": ["/products/edit", "/products/edit/:id"],
    "商品列表": ["/products"],
    "上下架": ["/products"],
    "文件上传": ["/products/edit", "/products/edit/:id", "/site-brand"],
    "库存查询/调整": ["/inventory"],
    "库存预警": ["/inventory"],
    "仓库": ["/inventory"],
    "订单列表": ["/orders"],
    "订单发货": ["/orders"],
    "售后管理": ["/aftersales"],
    "售后审核": ["/aftersales"],
    "系统设置": ["/settings"],
    "工作台": ["/dashboard"],
    "弹窗与提示": [],
}

V2_MODULE_PAGES = {
    "账号": ["/login", "/me", "/settings"],
    "首页": ["/", "/promo/:code"],
    "浏览": ["/category", "/search", "/product/:spuId"],
    "详情": ["/product/:spuId"],
    "购物车": ["/cart"],
    "交易": ["/checkout", "/pay/:orderId"],
    "订单": ["/orders", "/orders/:id"],
    "售后": ["/after-sales", "/after-sales/apply", "/after-sales/:id"],
    "个人中心": ["/me", "/addresses", "/favorites", "/history"],
    "评价": ["/product/:spuId"],
    "多端": ["/", "/category", "/cart", "/me"],
    "后台": ["/dashboard", "/products", "/orders", "/settings"],
    "全局": [],
}

V2_FR_PAGES = {
    "V2-FR-017": ["/customers"],
    "V2-FR-018": ["/site-brand"],
    "V2-FR-019": ["/home-slots"],
    "V2-FR-020": ["/settings"],
    "V2-FR-021": ["/orders"],
    "V2-FR-022": ["/orders"],
    "V2-FR-023": ["/products/edit", "/products/edit/:id"],
    "V2-FR-024": ["/in-out"],
    "V2-FR-025": ["/reviews"],
}
V2_ADMIN_FR = {f"V2-FR-{index:03d}" for index in range(17, 26)}

API_SUMMARY_FALLBACK = {
    "GET /api/addresses": "查询当前会员收货地址",
    "POST /api/addresses": "新增收货地址",
    "PUT /api/addresses/{id}": "修改收货地址",
    "DELETE /api/addresses/{id}": "删除收货地址",
    "PUT /api/addresses/{id}/default": "设置默认收货地址",
    "GET /api/after-sales": "查询当前会员售后单",
    "POST /api/after-sales": "申请售后",
    "GET /api/after-sales/{id}": "查询售后详情",
    "GET /api/cart": "查询购物车",
    "POST /api/cart/items": "加入购物车",
    "PUT /api/cart/items/{id}": "修改购物车条目",
    "DELETE /api/cart/items/{id}": "移除购物车条目",
    "POST /api/cart/clear-invalid": "清理失效购物车条目",
    "GET /api/categories": "查询类目树",
    "GET /api/favorites": "查询收藏列表",
    "POST /api/favorites/{spuId}": "收藏商品",
    "DELETE /api/favorites/{spuId}": "取消收藏",
    "GET /api/history": "查询浏览足迹",
    "DELETE /api/history": "清空浏览足迹",
    "GET /api/home": "首页聚合（品牌、运营位、推荐流）",
    "GET /api/orders": "查询当前会员订单",
    "POST /api/orders": "提交订单",
    "GET /api/orders/{id}": "查询订单详情",
    "POST /api/orders/{id}/cancel": "取消订单",
    "POST /api/orders/{id}/confirm": "确认收货",
    "GET /api/orders/{id}/logistics": "查询订单物流",
    "POST /api/payment/sandbox": "沙箱支付",
    "GET /api/payment/{orderId}/status": "查询支付状态",
    "GET /api/products": "分页查询商品",
    "GET /api/products/{spuId}": "查询商品详情（SKU/库存）",
    "GET /api/products/{spuId}/reviews": "查询商品评价",
    "GET /api/search": "关键词搜索商品",
    "GET /api/site/brand": "查询站点品牌",
    "POST /api/files/presign": "申请文件预签名上传",
    "POST /api/files/confirm": "确认文件上传",
    "PUT /admin/reviews/{id}/reply": "回复评价（商家回复）",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(url: str) -> str:
    url = re.sub(r"\$\{[^}]+\}", "{id}", url)
    url = url.split("?", 1)[0]
    return url if url.startswith("/") else f"/{url}"


def api_id(method: str, path: str) -> str:
    return f"api:{method.upper()}:{path}"


def fmt_api_id(value: str) -> str:
    parts = value.split(":", 2)
    return f"`{parts[1]} {parts[2]}`" if len(parts) == 3 else f"`{value}`"


def parse_api_functions(app: str) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    api_dir = ROOT / app / "src" / "api"
    for file in sorted(api_dir.glob("*.ts")):
        text = file.read_text(encoding="utf-8")
        parts = re.split(r"\nexport\s+function\s+", text)
        for part in parts[1:]:
            name = part.split("(", 1)[0].strip()
            block = part.split("\nexport\s+", 1)[0]
            urls = re.findall(r"url:\s*[`'\"]([^`'\"]+)", block)
            methods = re.findall(r"method:\s*['\"](\w+)", block)
            if not urls:
                continue
            if not methods:
                methods = ["GET"]
            calls = []
            for index, url in enumerate(urls):
                method = methods[min(index, len(methods) - 1)].upper()
                calls.append({"method": method, "path": normalize_path(url), "raw_url": url})
            result[f"{app}:{name}"] = calls
    result["_files"] = [str(path.relative_to(ROOT)) for path in sorted(api_dir.glob("*.ts"))]
    return result


def parse_view_imports(view_path: Path) -> list[tuple[str, str]]:
    text = view_path.read_text(encoding="utf-8")
    imports: list[tuple[str, str]] = []
    pattern = re.compile(r"import\s+(?:type\s+)?\{([^}]+)\}\s+from\s+['\"]@/api/([^'\"]+)['\"]", re.S)
    for match in pattern.finditer(text):
        module = match.group(2)
        for raw in match.group(1).split(","):
            name = raw.strip()
            if not name or name.startswith("type "):
                continue
            imports.append((module, name))
    return imports


def parse_requirements(md_path: Path, version: str) -> list[dict]:
    items = []
    for line in md_path.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("| FR-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5 or not cells[0].startswith("FR-"):
            continue
        items.append({
            "id": f"{version}-{cells[0]}",
            "version": version,
            "module": cells[1],
            "title": cells[2],
            "priority": cells[3],
            "section": cells[4],
        })
    return items


def make_chunk(chunk_id: str, kind: str, title: str, text: str, source: str, links: list[str], tags: list[str]) -> dict:
    return {"id": chunk_id, "type": kind, "title": title, "text": text, "source": source, "links": links, "tags": tags}


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    call_graph = read_json(CALL_GRAPH)
    endpoint_model = {f"{item['method']} {item['path']}": item for item in read_json(ENDPOINT_MODEL)["endpoints"]}
    openapi = read_json(OPENAPI)
    openapi_index = {}
    for path, methods in openapi.get("paths", {}).items():
        for method, operation in methods.items():
            openapi_index[f"{method.upper()} {path}"] = operation

    apis = []
    for endpoint in call_graph["endpoints"]:
        key = f"{endpoint['http']} {endpoint['path']}"
        model = endpoint_model.get(key, {})
        operation = openapi_index.get(key, {})
        params = []
        for param in operation.get("parameters", []):
            params.append({"name": param.get("name"), "in": param.get("in"), "required": bool(param.get("required")), "description": param.get("description", "")})
        apis.append({
            "id": api_id(endpoint["http"], endpoint["path"]),
            "method": endpoint["http"],
            "path": endpoint["path"],
            "tag": (operation.get("tags") or ["未分类"])[0],
            "summary": model.get("summary") or operation.get("summary") or API_SUMMARY_FALLBACK.get(key, ""),
            "auth": endpoint.get("auth", ""),
            "public": "免认证" in endpoint.get("auth", "") or endpoint.get("auth", "") in {"", "公开", "无"},
            "controller": endpoint.get("controller", ""),
            "method_name": endpoint.get("method", ""),
            "services": endpoint.get("services", []),
            "tables": endpoint.get("tables", []),
            "cross_api": endpoint.get("cross_api", []),
            "fe_callers": endpoint.get("fe_callers", []),
            "params": params,
            "dto_fields": model.get("dto_fields", []),
            "body_keys": model.get("body_keys", []),
            "codes": model.get("codes", []),
            "operation_id": operation.get("operationId", ""),
        })
    chat_api = {
        "id": "api:POST:/api/customer-service/chat",
        "method": "POST",
        "path": "/api/customer-service/chat",
        "tag": "C端AI助手",
        "summary": "商城 C 端 AI 助手对话（商品/知识/订单查询）",
        "auth": "免认证（可选会员 token 透传）",
        "public": True,
        "controller": "CustomerServiceController",
        "method_name": "chat",
        "services": ["CustomerServiceAgentClient"],
        "tables": [],
        "cross_api": [],
        "fe_callers": ["shang-mall/src/api/customer-service.ts"],
        "params": [],
        "dto_fields": ["message", "sessionId"],
        "body_keys": ["message", "sessionId"],
        "codes": [],
        "operation_id": "CustomerServiceController_chat",
    }
    if not any(api["path"] == chat_api["path"] for api in apis):
        apis.append(chat_api)
    reply_api = {
        "id": "api:PUT:/admin/reviews/{id}/reply",
        "method": "PUT",
        "path": "/admin/reviews/{id}/reply",
        "tag": "评价管理",
        "summary": "回复评价（商家回复）",
        "auth": "管理员 token",
        "public": False,
        "controller": "AdminOpsController",
        "method_name": "reviewReply",
        "services": ["ReviewAdminService"],
        "tables": ["commerce.review"],
        "cross_api": [],
        "fe_callers": ["shang-admin-web/src/api/reviews.ts"],
        "params": [],
        "dto_fields": ["reply"],
        "body_keys": ["reply"],
        "codes": ["UNAUTHORIZED", "NOT_FOUND", "BAD_REQUEST"],
        "operation_id": "AdminOpsController_reviewReply",
    }
    if not any(api["path"] == reply_api["path"] for api in apis):
        apis.append(reply_api)
    apis.sort(key=lambda item: (item["tag"], item["path"], item["method"]))
    api_by_key = {f"{item['method']} {item['path']}": item for item in apis}

    all_functions = {}
    for app in ("shang-mall", "shang-admin-web"):
        funcs = parse_api_functions(app)
        all_functions.update({key: value for key, value in funcs.items() if not key.startswith("_")})

    def endpoints_for_function(function_key: str) -> list[str]:
        matches = []
        for call in all_functions.get(function_key, []):
            candidates = [api for api in apis if api["method"] == call["method"] and api["path"] == call["path"]]
            if not candidates:
                pattern = re.compile("^" + re.escape(call["path"]).replace(r"\{id\}", r"[^/]+") + "$")
                candidates = [api for api in apis if api["method"] == call["method"] and pattern.match(api["path"])]
            matches.extend(api["id"] for api in candidates)
        return sorted(set(matches))

    page_api_overrides = {
        "mall:/login": ["api:POST:/api/auth/sms/send", "api:POST:/api/auth/login"],
        "mall:/me": ["api:GET:/api/me"],
        "mall:/settings": ["api:GET:/api/me", "api:PUT:/api/me", "api:POST:/api/auth/logout"],
        "admin:/login": ["api:POST:/admin/auth/login"],
        "admin:/reviews": ["api:GET:/admin/reviews", "api:PUT:/admin/reviews/{id}/status", "api:PUT:/admin/reviews/{id}/reply"],
    }
    pages = []
    for area, route_list in (("mall", MALL_PAGES), ("admin", ADMIN_PAGES)):
        for route, title, view in route_list:
            view_path = ROOT / view
            imports = parse_view_imports(view_path) if view_path.exists() else []
            modules = sorted({module for module, _ in imports})
            app_name = "shang-mall" if area == "mall" else "shang-admin-web"
            functions = sorted({f"{app_name}:{name}" for module, name in imports if f"{app_name}:{name}" in all_functions})
            api_ids = sorted({api for function in functions for api in endpoints_for_function(function)})
            api_ids = sorted(set(api_ids) | set(page_api_overrides.get(f"{area}:{route}", [])))
            pages.append({
                "id": f"page:{area}:{route}",
                "area": area,
                "route": route,
                "deployed_path": f"/admin{route}" if area == "admin" else route,
                "title": title,
                "view": view,
                "api_modules": modules,
                "api_functions": functions,
                "api_ids": api_ids,
            })

    pages.append({
        "id": "page:mall:ai-assistant",
        "area": "mall",
        "route": "(global)",
        "deployed_path": "所有 C 端页面右下角",
        "title": "AI 助手浮窗",
        "view": "shang-mall/src/components/AiAssistant.vue",
        "api_modules": ["customer-service"],
        "api_functions": ["shang-mall:chatWithAi"],
        "api_ids": ["api:POST:/api/customer-service/chat"],
    })

    requirements = []
    for path, version in ((ROOT / "docs/01-requirements/PRD-V1.0-后台管理.md", "V1"), (ROOT / "docs/01-requirements/PRD-V2.0-购物网站.md", "V2")):
        for item in parse_requirements(path, version):
            pages_for_req = V2_FR_PAGES.get(item["id"]) if version == "V2" else None
            if not pages_for_req:
                mapping = V2_MODULE_PAGES if version == "V2" else V1_MODULE_PAGES
                pages_for_req = mapping.get(item["module"], [])
            page_area = "admin" if version == "V1" or item["id"] in V2_ADMIN_FR else "mall"
            page_items = [p for p in pages if p["area"] == page_area and p["route"] in pages_for_req]
            api_ids = sorted({api for page in page_items for api in page["api_ids"]})
            requirements.append({**item, "pages": [page["id"] for page in page_items], "api_ids": api_ids, "source": str(path.relative_to(ROOT))})
    requirements.append({
        "id": "EXT-REVIEW-REPLY-001",
        "version": "EXT",
        "module": "评价管理",
        "title": "商品评价商家回复（管理端回复、C 端展示）",
        "priority": "P1",
        "section": "PRD-V2.1-评价商家回复",
        "pages": ["page:admin:/reviews", "page:mall:/product/:spuId"],
        "api_ids": ["api:GET:/admin/reviews", "api:PUT:/admin/reviews/{id}/reply", "api:GET:/api/products/{spuId}/reviews"],
        "source": "docs/01-requirements/PRD-V2.1-评价商家回复.md",
    })
    requirements.append({
        "id": "EXT-AI-001",
        "version": "EXT",
        "module": "AI助手",
        "title": "商城 C 端 AI 助手浮窗（商品/知识/订单）",
        "priority": "P1",
        "section": "agent_service + shang-customerservice",
        "pages": ["page:mall:ai-assistant"],
        "api_ids": ["api:POST:/api/customer-service/chat"],
        "source": "docs/03-ai/Agent落地进展.md",
    })
    requirements.sort(key=lambda item: (item["version"], item["id"]))

    # graph edges
    nodes = []
    edges = []
    for page in pages:
        nodes.append({"id": page["id"], "type": "page", "label": page["title"]})
        for req in requirements:
            if page["id"] in req["pages"]:
                edges.append({"from": req["id"], "to": page["id"], "type": "requirement_has_page"})
        for endpoint in page["api_ids"]:
            edges.append({"from": page["id"], "to": endpoint, "type": "page_calls_api"})
    for api in apis:
        nodes.append({"id": api["id"], "type": "api", "label": f"{api['method']} {api['path']}"})
        if api["controller"]:
            controller = f"controller:{api['controller']}"
            nodes.append({"id": controller, "type": "controller", "label": api["controller"]})
            edges.append({"from": api["id"], "to": controller, "type": "handled_by"})
        for service in api["services"]:
            nodes.append({"id": f"service:{service}", "type": "service", "label": service})
            edges.append({"from": api["id"], "to": f"service:{service}", "type": "calls_service"})
        for table in api["tables"]:
            nodes.append({"id": f"table:{table}", "type": "table", "label": table})
            edges.append({"from": api["id"], "to": f"table:{table}", "type": "accesses_table"})
    for req in requirements:
        nodes.append({"id": req["id"], "type": "requirement", "label": f"{req['id']} {req['title']}"})
        for endpoint in req["api_ids"]:
            edges.append({"from": req["id"], "to": endpoint, "type": "requirement_has_api"})
    # de-duplicate graph nodes/edges
    node_map = {node["id"]: node for node in nodes}
    nodes = list(node_map.values())
    edge_map = {(edge["from"], edge["to"], edge["type"]): edge for edge in edges}
    edges = list(edge_map.values())
    graph = {"generated_at": datetime.now(timezone.utc).isoformat(), "nodes": nodes, "edges": edges}

    requirements_data = {"generated_at": datetime.now(timezone.utc).isoformat(), "count": len(requirements), "items": requirements}
    apis_data = {"generated_at": datetime.now(timezone.utc).isoformat(), "count": len(apis), "items": apis}
    pages_data = {"generated_at": datetime.now(timezone.utc).isoformat(), "count": len(pages), "items": pages}
    (DATA / "apis.json").write_text(json.dumps(apis_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "pages.json").write_text(json.dumps(pages_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "requirements.json").write_text(json.dumps(requirements_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")

    chunks = []
    for api in apis:
        chunks.append(make_chunk(
            api["id"], "api", f"{api['method']} {api['path']}",
            f"{api['method']} {api['path']}\n摘要：{api['summary']}\n鉴权：{api['auth'] or '未标注'}\n"
            f"控制器：{api['controller']}#{api['method_name']}\n服务：{', '.join(api['services']) or '无'}\n"
            f"表：{', '.join(api['tables']) or '无'}\n参数：{', '.join(p['name'] for p in api['params']) or '无'}",
            "api_testcases/artifacts/call-graph.json", [f"tag:{api['tag']}"], [api["tag"], "api"],
        ))
    for page in pages:
        chunks.append(make_chunk(
            page["id"], "page", f"{page['area']} {page['title']} {page['route']}",
            f"页面：{page['title']}\n路由：{page['deployed_path']}\n视图：{page['view']}\n"
            f"API 模块：{', '.join(page['api_modules']) or '无'}\n"
            f"调用接口：{', '.join(page['api_ids']) or '无'}",
            page["view"], page["api_ids"], [page["area"], "page"],
        ))
    for req in requirements:
        chunks.append(make_chunk(
            req["id"], "requirement", f"{req['id']} {req['title']}",
            f"版本：{req['version']}\n模块：{req['module']}\n优先级：{req['priority']}\n"
            f"详设：{req['section']}\n页面：{', '.join(req['pages']) or '无'}\n接口：{', '.join(req['api_ids']) or '无'}",
            req["source"], req["pages"] + req["api_ids"], [req["version"], req["module"], "requirement"],
        ))
    rules = [
        ("rule:order-state", "订单状态机", "待付款→待发货（支付成功）；待付款→已关闭（取消/15分钟超时）；待发货→待收货（后台发货并扣库存）；待收货→已完成（确认收货）；待收货/已完成→售后处理中（售后单驱动，不改订单主状态）。", "docs/06-baseline/02-业务规则与状态机.md"),
        ("rule:after-sale-state", "售后状态机", "待审核→退款中（审核通过）；待审核→已拒绝（拒绝且必须填意见）；退款中→已完成（模拟退款成功）；退款中→退款失败；退款失败→退款中；已拒绝→待审核（修改申诉）。", "docs/06-baseline/02-业务规则与状态机.md"),
        ("rule:stock", "库存不变式", "physical >= locked >= 0；available = physical - locked（不落库）。提交订单锁库存，取消/超时释放，发货时总库存与锁定同时扣减并写 stock_log。", "docs/06-baseline/02-业务规则与状态机.md"),
        ("rule:order-submit", "下单序列", "校验地址/SKU/库存 → 写 order + order_item → 锁定 stock 并写 stock_log → 清空购物车选中项 → 生成待付款订单；任一步失败整单回滚。", "docs/06-baseline/02-业务规则与状态机.md"),
        ("rule:product-visible", "商品可见性", "C 端只展示 SPU status=ON 且 deleted=false；SKU 只展示 status=ENABLED；可用库存=physical-locked；下架/删除/无 SKU/库存为 0 的可见性按 PRD 与 As-built 规则处理。", "docs/06-baseline/02-业务规则与状态机.md"),
        ("rule:auth", "认证与权限", "管理端 /admin/** 使用管理员 JWT；C 端 /api/** 使用顾客 JWT，公开读白名单见 SecurityConfig；令牌 access TTL 900s、refresh TTL 7d；管理端登录失败 5 次锁定 15 分钟。", "docs/06-baseline/02-业务规则与状态机.md"),
        ("rule:payment", "沙箱支付", "POST /api/payment/sandbox {orderId} 将待付款订单置为已支付；不产生真实交易；支付成功后订单进入待发货。", "docs/06-baseline/02-业务规则与状态机.md"),
        ("rule:review", "评价规则", "仅已完成订单可评价；同一订单/商品不可重复评价；评价默认待审核/可见状态按实现；评分 1-5，内容/图片需校验。", "docs/06-baseline/02-业务规则与状态机.md"),
        ("rule:cart", "购物车规则", "购物车按 customer 唯一；条目按 skuId 合并；缺 skuId 拒绝；失效商品可清理；选中项参与结算；下单后清空选中项。", "docs/06-baseline/02-业务规则与状态机.md"),
        ("rule:address", "地址规则", "一个顾客可有多个地址；默认地址唯一；下单必须传有效 addressId；地址 id 为雪花号，前端必须按字符串处理。", "docs/06-baseline/02-业务规则与状态机.md"),
        ("rule:negative", "实现缺口/负面清单", "存在非法状态转移可达、库存校验缺口、校验不一致、死代码/未接线等已知问题；做新需求与用例时必须先读 06-baseline 第 10 节，不能把设计当实现。", "docs/06-baseline/02-业务规则与状态机.md"),
        ("rule:review-reply", "评价商家回复", "商家回复只更新 commerce.review.merchant_reply/replied_at，不改变评价 rating/status/content/pics；C 端只展示 VISIBLE 评价及其回复；回复 1–500 字，空内容/超长返回 40000；管理端操作写 @OpLog(module=review, action=reply)。", "docs/01-requirements/PRD-V2.1-评价商家回复.md"),
    ]
    for chunk_id, title, text, source in rules:
        chunks.append(make_chunk(chunk_id, "rule", title, text, source, [], ["business-rule"]))
    with (DATA / "chunks.jsonl").open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    # generated Markdown catalogs
    by_tag = defaultdict(list)
    for api in apis:
        by_tag[api["tag"]].append(api)
    api_lines = [f"# API 目录（{len(apis)} endpoints）", "", f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}；来源：`api_testcases/artifacts/call-graph.json` + `endpoint-model.json` + OpenAPI。", ""]
    for tag in sorted(by_tag):
        api_lines += [f"## {tag}", "", "| 方法 | 路径 | 摘要 | 鉴权 | Controller / Service | 表 |", "|---|---|---|---|---|---|"]
        for api in by_tag[tag]:
            api_lines.append(f"| {api['method']} | `{api['path']}` | {api['summary'] or '-'} | {api['auth'] or '-'} | {api['controller']}#{api['method_name']} / {', '.join(api['services']) or '-'} | {', '.join(api['tables']) or '-'} |")
        api_lines.append("")
    (WIKI / "03-api-catalog.md").write_text("\n".join(api_lines), encoding="utf-8")

    page_lines = ["# 页面 ↔ API 映射", "", "## C 端（shang-mall）", "", "| 路由 | 页面 | 视图 | 调用接口 |", "|---|---|---|---|"]
    for page in [p for p in pages if p["area"] == "mall"]:
        page_lines.append(f"| `{page['route']}` | {page['title']} | `{page['view'].split('/')[-1]}` | {', '.join(fmt_api_id(api) for api in page['api_ids']) or '-'} |")
    page_lines += ["", "## 管理端（shang-admin-web，部署前缀 `/admin`）", "", "| 路由 | 页面 | 视图 | 调用接口 |", "|---|---|---|---|"]
    for page in [p for p in pages if p["area"] == "admin"]:
        page_lines.append(f"| `{page['deployed_path']}` | {page['title']} | `{page['view'].split('/')[-1]}` | {', '.join(fmt_api_id(api) for api in page['api_ids']) or '-'} |")
    (WIKI / "04-page-map.md").write_text("\n".join(page_lines), encoding="utf-8")

    req_lines = ["# 需求目录（V1 + V2 + 扩展）", "", "> ID 前缀 `V1-` / `V2-` 区分版本；页面和接口由实际路由/调用图反推。", ""]
    for version in ("V1", "V2", "EXT"):
        req_lines += [f"## {version}", "", "| ID | 模块 | 功能 | 优先级 | 页面 | 接口数 |", "|---|---|---|---|---|---:|"]
        for req in [r for r in requirements if r["version"] == version]:
            req_lines.append(f"| {req['id']} | {req['module']} | {req['title']} | {req['priority']} | {', '.join(req['pages']) or '-'} | {len(req['api_ids'])} |")
        req_lines.append("")
    (WIKI / "02-requirements.md").write_text("\n".join(req_lines), encoding="utf-8")

    trace_lines = ["# 需求-页面-接口追溯矩阵", "", "> 只列有页面落点的需求；接口为页面实际调用集合，不等同于需求全部接口。", "", "| 需求 | 页面 | 接口数 | 代表接口 |", "|---|---|---:|---|"]
    for req in requirements:
        if not req["pages"]:
            continue
        sample = ", ".join(fmt_api_id(api) for api in req["api_ids"][:5]) or "-"
        trace_lines.append(f"| {req['id']} {req['title']} | {', '.join(req['pages'])} | {len(req['api_ids'])} | {sample} |")
    (WIKI / "05-traceability-matrix.md").write_text("\n".join(trace_lines), encoding="utf-8")

    controller_rows = defaultdict(lambda: {"apis": 0, "services": set(), "tables": set()})
    for api in apis:
        row = controller_rows[api["controller"]]
        row["apis"] += 1
        row["services"].update(api["services"])
        row["tables"].update(api["tables"])
    code_lines = ["# 代码地图", "", "| Controller | 端点数 | Service | 表 |", "|---|---:|---|---|"]
    for controller in sorted(controller_rows):
        row = controller_rows[controller]
        code_lines.append(f"| {controller} | {row['apis']} | {', '.join(sorted(row['services'])) or '-'} | {', '.join(sorted(row['tables'])) or '-'} |")
    (WIKI / "07-code-map.md").write_text("\n".join(code_lines), encoding="utf-8")

    print(f"apis={len(apis)} pages={len(pages)} requirements={len(requirements)} chunks={len(chunks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
