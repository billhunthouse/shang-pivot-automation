"""评价商家回复 UI 闭环：管理端回复 → 商城商品详情展示。

运行：
  RUN_UI=1 ADMIN_UI_URL=http://127.0.0.1:5173 MALL_UI_URL=http://127.0.0.1:5174 \
  ADMIN_TEST_ACCOUNT=admin ADMIN_TEST_PASSWORD=... \
  python3 -m pytest tests/ui/test_review_reply_ui.py --alluredir ...
"""
from __future__ import annotations

import os
import time

import allure
import pytest

pytestmark = pytest.mark.ui


def _screenshot(page, name: str) -> None:
    try:
        allure.attach(page.screenshot(full_page=True), name=name, attachment_type=allure.attachment_type.PNG)
    except Exception:
        pass


@allure.epic("尚品汇 · 评价商家回复")
@allure.feature("评价管理 UI")
@allure.story("管理端回复到 C 端展示")
@allure.title("UI-REPLY-001 管理员回复评价，商品详情出现商家回复")
@allure.severity(allure.severity_level.CRITICAL)
def test_admin_reply_visible_on_product_page():
    if os.getenv("RUN_UI", "0") != "1":
        pytest.skip("RUN_UI != 1; Playwright UI layer is opt-in")
    account = os.getenv("ADMIN_TEST_ACCOUNT", "")
    password = os.getenv("ADMIN_TEST_PASSWORD", "")
    if not account or not password:
        pytest.skip("未设置 ADMIN_TEST_ACCOUNT / ADMIN_TEST_PASSWORD")
    admin_url = os.getenv("ADMIN_UI_URL", "http://127.0.0.1:5173").rstrip("/")
    mall_url = os.getenv("MALL_UI_URL", "http://127.0.0.1:5174").rstrip("/")
    reply = f"自动化测试商家回复UI-{int(time.time())}"

    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as manager:
        browser = manager.chromium.launch(headless=os.getenv("UI_HEADLESS", "true") != "false")
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        try:
            with allure.step("管理员登录"):
                page.goto(f"{admin_url}/login", wait_until="domcontentloaded", timeout=30_000)
                page.locator('input[name="username"]').fill(account)
                page.locator('input[name="password"]').fill(password)
                page.locator('button[type="submit"]').click()
                page.wait_for_url("**/dashboard", timeout=15_000)
                _screenshot(page, "管理员登录.png")

            with allure.step("打开评价管理并定位评价"):
                page.goto(f"{admin_url}/reviews", wait_until="domcontentloaded", timeout=30_000)
                page.get_by_placeholder("商品名 / 会员手机尾号").fill("打工人")
                page.get_by_role("button", name="查询").click()
                row = page.locator("tr", has_text="打工人神器").first
                row.wait_for(state="visible", timeout=15_000)
                row.get_by_role("button", name="回复").click()
                _screenshot(page, "评价管理-定位评价.png")

            with allure.step("填写并保存商家回复"):
                dialog = page.locator(".modal-panel")
                dialog.locator("textarea").fill(reply)
                dialog.get_by_role("button", name="保存回复").click()
                page.wait_for_timeout(800)
                assert page.locator(".modal-panel").count() == 0
                _screenshot(page, "回复已保存.png")

            with allure.step("C 端商品详情展示商家回复"):
                page.goto(f"{mall_url}/product/127", wait_until="domcontentloaded", timeout=30_000)
                page.get_by_text(reply).wait_for(state="visible", timeout=15_000)
                assert page.locator(".merchant-reply").filter(has_text=reply).count() == 1
                _screenshot(page, "商家回复-C端展示.png")
        except Exception:
            _screenshot(page, "商家回复-失败现场.png")
            raise
        finally:
            context.close()
            browser.close()
