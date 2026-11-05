"""Agent 工具层：只通过 REST API 访问 commerce，不直读 schema。"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
FAQ_FILE = ROOT / "data" / "faq.json"


class ToolError(RuntimeError):
    pass


class ToolAuthError(ToolError):
    pass


@dataclass
class ToolResult:
    name: str
    args: dict[str, Any]
    result: Any
    status: str
    latency_ms: float
    retrieval: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "name": self.name,
            "args": self.args,
            "result": self.result,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 3),
        }
        if self.retrieval is not None:
            data["retrieval"] = self.retrieval
        return data


def search_faq_rows(query: str, limit: int = 2) -> list[dict]:
    rows = json.loads(FAQ_FILE.read_text(encoding="utf-8"))
    tokens = [t for t in query.replace("？", " ").replace("?", " ").split() if t]
    scored = []
    for row in rows:
        haystack = f"{row['question']} {row['answer']}"
        score = sum(1 for token in tokens if token in haystack)
        score += sum(1 for keyword in row.get("keywords", []) if keyword in query)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:limit]] or rows[:1]


class CommerceTools:
    def __init__(self, base_url: str, knowledge_base=None):
        self.base_url = base_url.rstrip("/")
        self.knowledge_base = knowledge_base

    async def _get(self, path: str, token: str | None = None, params: dict | None = None) -> Any:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = token if token.startswith("Bearer ") else f"Bearer {token}"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.base_url}{path}", headers=headers, params=params or {})
        if response.status_code == 401:
            raise ToolAuthError("登录态无效或缺失")
        if response.status_code >= 400:
            raise ToolError(f"HTTP {response.status_code}: {response.text[:300]}")
        body = response.json()
        if body.get("code") not in (0, "0"):
            raise ToolError(f"业务失败 code={body.get('code')} msg={body.get('msg')}")
        return body.get("data")

    async def search_products(self, query: str, limit: int = 3) -> ToolResult:
        started = time.perf_counter()
        q = (query or "").strip()
        if q and not any(word in q for word in ["找", "推荐", "搜索", "买", "商品"]):
            data = await self._get("/search", params={"q": q, "page": 1, "size": limit})
        elif q:
            keyword = next((w for w in ["帐篷", "咖啡", "笔记本", "口红", "跑步鞋", "鞋"] if w in q), "")
            data = await self._get("/search", params={"q": keyword, "page": 1, "size": limit}) if keyword else await self._get("/products", params={"page": 1, "size": limit, "sort": "sold"})
        else:
            data = await self._get("/products", params={"page": 1, "size": limit, "sort": "sold"})
        records = (data or {}).get("records") or []
        products = [
            {
                "spuId": str(item.get("spuId") or ""),
                "name": item.get("name"),
                "price": item.get("price"),
                "priceMax": item.get("priceMax"),
            }
            for item in records[:limit]
        ]
        return ToolResult("searchProducts", {"query": q, "limit": limit}, products, "ok", (time.perf_counter() - started) * 1000)

    async def get_orders(self, token: str | None, limit: int = 5) -> ToolResult:
        if not token:
            raise ToolAuthError("查询订单需要登录")
        started = time.perf_counter()
        data = await self._get("/orders", token=token, params={"page": 1, "size": limit})
        records = (data or {}).get("records") or []
        orders = [
            {
                "orderId": str(item.get("id") or ""),
                "orderNo": item.get("orderNo"),
                "status": item.get("status"),
                "payAmount": item.get("payAmount"),
            }
            for item in records[:limit]
        ]
        return ToolResult("getOrders", {"hasToken": True, "limit": limit}, orders, "ok", (time.perf_counter() - started) * 1000)

    async def get_after_sales(self, token: str | None, limit: int = 5) -> ToolResult:
        if not token:
            raise ToolAuthError("查询售后需要登录")
        started = time.perf_counter()
        data = await self._get("/after-sales", token=token, params={"page": 1, "size": limit})
        records = (data or {}).get("records") or []
        rows = [
            {
                "id": str(item.get("id") or ""),
                "type": item.get("type"),
                "status": item.get("status"),
                "reason": item.get("reason"),
            }
            for item in records[:limit]
        ]
        return ToolResult("getAfterSales", {"hasToken": True, "limit": limit}, rows, "ok", (time.perf_counter() - started) * 1000)

    async def search_faq(self, query: str, limit: int = 2) -> ToolResult:
        started = time.perf_counter()
        rows, retrieval = await faq_search(self.knowledge_base, query, limit)
        return ToolResult(
            "searchFaq",
            {"query": query, "limit": limit},
            rows,
            "ok",
            (time.perf_counter() - started) * 1000,
            retrieval,
        )


async def faq_search(knowledge_base, query: str, limit: int) -> tuple[list[dict], dict]:
    """优先走向量库；失败时降级关键词检索，并把降级原因写进 retrieval trace。"""
    if knowledge_base is None:
        rows = search_faq_rows(query, limit)
        return rows, {
            "backend": "keyword",
            "query": query,
            "hits": [{"title": row["question"], "source": "faq.json", "score": None} for row in rows],
        }
    try:
        hits = await knowledge_base.search(query, limit)
        rows = [
            {
                "question": hit["title"],
                "answer": hit["content"],
                "source": hit["source"],
                "score": hit["score"],
            }
            for hit in hits
        ]
        return rows, {
            "backend": knowledge_base.backend,
            "query": query,
            "hits": [
                {"title": hit["title"], "source": hit["source"], "score": hit["score"]}
                for hit in hits
            ],
        }
    except Exception as exc:  # noqa: BLE001 - 检索失败降级关键词，不让整个 Agent 失败
        rows = search_faq_rows(query, limit)
        return rows, {
            "backend": "keyword",
            "query": query,
            "fallback": True,
            "error": f"{type(exc).__name__}: {str(exc)[:200]}",
            "hits": [{"title": row["question"], "source": "faq.json", "score": None} for row in rows],
        }


class FakeCommerceTools:
    """评测/单测用确定性工具；不访问网络。"""

    def __init__(self, knowledge_base=None):
        self.knowledge_base = knowledge_base

    async def search_products(self, query: str, limit: int = 3) -> ToolResult:
        return ToolResult(
            "searchProducts",
            {"query": query, "limit": limit},
            [
                {"spuId": "101", "name": "轻量徒步帐篷", "price": 399, "priceMax": 499},
                {"spuId": "102", "name": "通勤跑鞋", "price": 299, "priceMax": None},
            ][:limit],
            "ok",
            8.0,
        )

    async def get_orders(self, token: str | None, limit: int = 5) -> ToolResult:
        if not token:
            raise ToolAuthError("查询订单需要登录")
        return ToolResult(
            "getOrders",
            {"hasToken": True, "limit": limit},
            [{"orderId": "1", "orderNo": "O202611050001", "status": "PENDING_PAY", "payAmount": 399}],
            "ok",
            6.0,
        )

    async def get_after_sales(self, token: str | None, limit: int = 5) -> ToolResult:
        if not token:
            raise ToolAuthError("查询售后需要登录")
        return ToolResult(
            "getAfterSales",
            {"hasToken": True, "limit": limit},
            [{"id": "1", "type": "RETURN", "status": "PENDING", "reason": "不合脚"}],
            "ok",
            5.0,
        )

    async def search_faq(self, query: str, limit: int = 2) -> ToolResult:
        rows, retrieval = await faq_search(self.knowledge_base, query, limit)
        return ToolResult(
            "searchFaq",
            {"query": query, "limit": limit},
            rows,
            "ok",
            2.0,
            retrieval,
        )
