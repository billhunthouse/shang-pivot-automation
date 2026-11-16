"""UI 测试目录 fixtures：浏览器会话、页面冒烟、评价数据恢复。"""
from __future__ import annotations

import os

import pytest
from playwright.sync_api import sync_playwright

from .ui_support import ADMIN_UI, MALL_UI, admin_api, find_review, login_admin, login_customer, set_reply, ui_session


@pytest.fixture
def ui():
    with ui_session() as session:
        yield session


@pytest.fixture(scope="module")
def smoke_pages():
    """页面冒烟复用登录态：guest / customer / admin 各一个 context。

    只做只读导航，测试之间不共享业务数据；页面之间用 goto 切换。
    """
    if os.getenv("RUN_UI", "0") != "1":
        pytest.skip("RUN_UI != 1；UI 层按需启用")
    headless = os.getenv("UI_HEADLESS", "true").lower() != "false"
    with sync_playwright() as manager:
        browser = manager.chromium.launch(headless=headless)
        guest_context = browser.new_context(viewport={"width": 1440, "height": 900})
        customer_context = browser.new_context(viewport={"width": 1440, "height": 900})
        admin_context = browser.new_context(viewport={"width": 1440, "height": 900})
        guest = guest_context.new_page()
        customer = customer_context.new_page()
        admin = admin_context.new_page()
        login_customer(customer, redirect="/")
        login_admin(admin)
        try:
            yield {
                "guest": guest,
                "customer": customer,
                "admin": admin,
                "browser": browser,
                "base": {"mall": MALL_UI, "admin": ADMIN_UI},
            }
        finally:
            guest_context.close()
            customer_context.close()
            admin_context.close()
            browser.close()


@pytest.fixture(scope="module")
def review_api():
    with admin_api() as api:
        yield api


@pytest.fixture(scope="module")
def review_target(review_api):
    """固定可见评价 8503；测试结束后恢复原始回复，避免污染数据。"""
    record = find_review(review_api, 8503, status="VISIBLE")
    original = record.get("merchantReply") or ""
    yield record
    if original:
        set_reply(review_api, 8503, original)
