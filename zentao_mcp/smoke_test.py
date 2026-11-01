#!/usr/bin/env python3
"""Read/create/update/delete smoke test against a live ZenTao instance.

Usage:
  ZENTAO_BASE_URL=http://... ZENTAO_PASSWORD_FILE=... .venv/bin/python smoke_test.py
"""
from __future__ import annotations

import os
import sys

from zentao_client import ZenTaoClient


def main() -> int:
    client = ZenTaoClient.from_env()
    print("products:", client.list_products(limit=5).get("total"))
    print("test cases:", client.list_test_cases(1, limit=5).get("total"))

    case = client.create_test_case(
        1,
        "MCP smoke test（可删除）",
        steps=[
            {"step": "打开首页", "expect": "返回 200"},
            {"step": "检查标题", "expect": "标题存在"},
        ],
        precondition="smoke test",
    )
    case_id = int(case["id"])
    print("created:", case_id, "steps:", len(case.get("steps") or []))
    try:
        print("title:", client.get_test_case(case_id).get("title"))
        client.update_test_case(case_id, keywords="mcp-smoke")
        print("updated keywords: ok")
        try:
            client.update_test_case_status(case_id, "blocked")
        except Exception as exc:  # expected on ZenTao 22.6
            print("status update limitation:", str(exc)[:100])
    finally:
        client._request("DELETE", f"/testcases/{case_id}")
        print("cleanup: ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
