"""41 个页面的 UI 冒烟：路由可达、关键内容渲染、无页面级错误、逐页截图。"""
from __future__ import annotations

import allure
import pytest
from playwright.sync_api import expect

from .page_catalog import PAGE_CATALOG
from .ui_support import step

pytestmark = [pytest.mark.ui, pytest.mark.smoke, pytest.mark.regression]


def _params():
    return [
        pytest.param(item, id=f"{item['case_id']}-{item['title']}")
        for item in PAGE_CATALOG
    ]


@allure.epic("尚品汇 · UI 自动化")
@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("页面冒烟")
@allure.feature("页面可达性")
@allure.story("全站页面冒烟")
@allure.title("UI-PAGE 全站页面可达性与关键内容")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("UI", "P0", "page-smoke")
@pytest.mark.parametrize("item", _params())
def test_page_smoke(smoke_pages, item):
    page = smoke_pages[item["role"]]
    case_id = item["case_id"]
    allure.dynamic.title(f"{case_id} {item['title']}可访问并渲染关键内容")

    with step(page, f"访问{item['title']} {item['path']}"):
        page.goto(f"{smoke_pages['base'][item['area']]}{item['path']}", wait_until="domcontentloaded", timeout=30_000)
        if item.get("special") == "ai":
            page.get_by_role("button", name="打开 AI 助手").click()
        expect(page.locator("body")).to_contain_text(item["expect"], timeout=15_000)

    with step(page, "断言无页面级错误"):
        body = page.locator("body").inner_text()
        assert "页面不存在" not in body
        assert "ChunkLoadError" not in body
        assert "Failed to fetch dynamically imported module" not in body
