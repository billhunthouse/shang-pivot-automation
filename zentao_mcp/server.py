#!/usr/bin/env python3
"""ZenTao MCP server (stdio).

Tools are intentionally small and explicit:
- products / test cases: read, create, update
- test case status: best-effort (ZenTao 22.6 API limitation documented)
- bugs: list/get and lifecycle actions (resolve/close/assign/confirm/active)
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from zentao_client import ZenTaoClient, ZenTaoError

mcp = FastMCP(
    "zentao",
    instructions=(
        "禅道 MCP。先用 zentao_list_products 找 product_id，再查/建用例。"
        "写入类工具会直接修改禅道数据，调用前确认目标和字段。"
        "用例 status 在禅道 22.6 API 中不能直接改，请优先用 bug 生命周期动作或 UI。"
    ),
)

_client: ZenTaoClient | None = None


def client() -> ZenTaoClient:
    global _client
    if _client is None:
        _client = ZenTaoClient.from_env()
    return _client


def ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def fail(exc: Exception) -> dict[str, Any]:
    return {"ok": False, "error": str(exc), "type": type(exc).__name__}


def guarded(fn):
    try:
        return ok(fn())
    except ZenTaoError as exc:
        return fail(exc)
    except Exception as exc:  # keep MCP responses readable instead of crashing
        return fail(exc)


@mcp.tool()
def zentao_ping() -> dict[str, Any]:
    """检查禅道地址、账号和 token 是否可用。"""
    def run():
        data = client().list_products(limit=1)
        return {"baseUrl": client().base_url, "products": data}

    return guarded(run)


@mcp.tool()
def zentao_list_products(page: int = 1, limit: int = 20) -> dict[str, Any]:
    """列出禅道产品。product_id 是后续查/建用例的必填参数。"""
    return guarded(lambda: client().list_products(page=page, limit=limit))


@mcp.tool()
def zentao_list_test_cases(
    product_id: int,
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
) -> dict[str, Any]:
    """列出某产品下的测试用例。status 可选 wait/normal/blocked/investigate。"""
    return guarded(
        lambda: client().list_test_cases(
            product_id=product_id, page=page, limit=limit, status=status
        )
    )


@mcp.tool()
def zentao_get_test_case(case_id: int | str) -> dict[str, Any]:
    """查看单个测试用例详情。case_id 支持 1 或列表返回的 case_1。"""
    return guarded(lambda: client().get_test_case(case_id=case_id))


@mcp.tool()
def zentao_create_test_case(
    product_id: int,
    title: str,
    steps: list[dict[str, str]] | None = None,
    case_type: str = "feature",
    stage: str = "test",
    priority: int = 3,
    precondition: str = "",
    keywords: str = "",
    module_id: int = 0,
) -> dict[str, Any]:
    """创建测试用例。

    steps 示例:
    [{"step": "打开首页", "expect": "返回 200"},
     {"step": "检查标题", "expect": "标题存在"}]

    每个 step 也支持 type=step/group/item。
    创建前请确认 product_id 和标题，避免重复建用例。
    """
    return guarded(
        lambda: client().create_test_case(
            product_id=product_id,
            title=title,
            case_type=case_type,
            stage=stage,
            priority=priority,
            precondition=precondition,
            keywords=keywords,
            module_id=module_id,
            steps=steps,
        )
    )


@mcp.tool()
def zentao_update_test_case(
    case_id: int | str,
    title: str | None = None,
    precondition: str | None = None,
    keywords: str | None = None,
    priority: int | None = None,
) -> dict[str, Any]:
    """更新测试用例的可编辑字段（标题/前置条件/关键词/优先级）。

    禅道 22.6 API 不支持直接替换步骤；步骤请用 UI 编辑。
    """
    return guarded(
        lambda: client().update_test_case(
            case_id=case_id,
            title=title,
            precondition=precondition,
            keywords=keywords,
            priority=priority,
        )
    )


@mcp.tool()
def zentao_update_test_case_status(case_id: int | str, status: str) -> dict[str, Any]:
    """尝试更新用例状态（wait/normal/blocked/investigate）。

    注意：禅道 22.6 的 API 没有直接修改用例 status 的入口。
    本工具会先改、再读回验证；若未生效会返回明确错误。
    生产建议：用评审/执行动作，或在禅道 UI 修改。
    """
    return guarded(lambda: client().update_test_case_status(case_id=case_id, status=status))


@mcp.tool()
def zentao_list_bugs(product_id: int, page: int = 1, limit: int = 20) -> dict[str, Any]:
    """列出某产品下的 Bug。"""
    return guarded(lambda: client().list_bugs(product_id=product_id, page=page, limit=limit))


@mcp.tool()
def zentao_get_bug(bug_id: int) -> dict[str, Any]:
    """查看单个 Bug 详情。"""
    return guarded(lambda: client().get_bug(bug_id=bug_id))


@mcp.tool()
def zentao_bug_action(
    bug_id: int,
    action: str,
    fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """执行 Bug 生命周期动作。

    action: resolve / close / assign / confirm / active
    fields: 传给禅道 API 的字段，例如:
      resolve -> {"resolution": "fixed", "resolvedBuild": "trunk"}
      close   -> {"closedReason": "fixed"}
      assign  -> {"assignedTo": "admin"}
      active  -> {"comment": "重新打开"}
    """
    return guarded(lambda: client().bug_action(bug_id=bug_id, action=action, fields=fields))


@mcp.tool()
def zentao_list_test_tasks(project_id: int, page: int = 1, limit: int = 20) -> dict[str, Any]:
    """列出项目下的测试单。"""
    return guarded(
        lambda: client().list_test_tasks(project_id=project_id, page=page, limit=limit)
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
