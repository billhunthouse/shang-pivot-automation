"""Playwright + Allure 3 的 UI 测试基础设施。

设计目标：
- 每个 allure.step 自动截图；
- 失败时保存管理端/商城两端现场；
- 管理员与顾客使用独立 browser context，互不污染；
- 统一登录、API 数据准备和断言辅助。
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from urllib.parse import quote

import allure
import requests
from playwright.sync_api import Browser, BrowserContext, Page, expect, sync_playwright

ADMIN_UI = os.getenv("ADMIN_UI_URL", "http://127.0.0.1:5173").rstrip("/")
MALL_UI = os.getenv("MALL_UI_URL", "http://127.0.0.1:5174").rstrip("/")
ADMIN_BASE = os.getenv("ADMIN_BASE_URL", "http://127.0.0.1:8086/admin").rstrip("/")
MALL_BASE = os.getenv("MALL_BASE_URL", "http://127.0.0.1:8086").rstrip("/")
ADMIN_ACCOUNT = os.getenv("ADMIN_TEST_ACCOUNT", "")
ADMIN_PASSWORD = os.getenv("ADMIN_TEST_PASSWORD", "")
CUSTOMER_PHONE = os.getenv("MALL_TEST_PHONE", "13800000001")
CUSTOMER_CODE = os.getenv("MALL_TEST_CODE", "123456")
UI_HEADLESS = os.getenv("UI_HEADLESS", "true").lower() != "false"
ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", "artifacts")) / "ui-failures"


@dataclass
class UiSession:
    browser: Browser
    admin_context: BrowserContext
    mall_context: BrowserContext
    admin: Page
    mall: Page


def _attach_screenshot(page: Page, name: str, full_page: bool = True) -> None:
    try:
        allure.attach(
            page.screenshot(full_page=full_page),
            name=f"{name}.png",
            attachment_type=allure.attachment_type.PNG,
        )
    except Exception:
        # 截图不能掩盖原始断言失败
        pass


def save_failure_artifacts(page: Page, name: str) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() * 1000)
    path = ARTIFACT_DIR / f"{stamp}-{name}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
    except Exception:
        pass
    try:
        allure.attach(
            f"URL: {page.url}\nTITLE: {page.title()}\n",
            name=f"{name}-现场信息.txt",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception:
        pass


@contextmanager
def step(page: Page, title: str, full_page: bool = True) -> Iterator[None]:
    """Allure 步骤 + 步骤结束截图（失败也会截图）。"""
    with allure.step(title):
        try:
            yield
        finally:
            _attach_screenshot(page, title, full_page=full_page)


@contextmanager
def ui_session() -> Iterator[UiSession]:
    if os.getenv("RUN_UI", "0") != "1":
        import pytest

        pytest.skip("RUN_UI != 1；UI 层按需启用")
    with sync_playwright() as manager:
        browser = manager.chromium.launch(headless=UI_HEADLESS)
        admin_context = browser.new_context(viewport={"width": 1440, "height": 900})
        mall_context = browser.new_context(viewport={"width": 1440, "height": 900})
        admin = admin_context.new_page()
        mall = mall_context.new_page()
        session = UiSession(browser, admin_context, mall_context, admin, mall)
        try:
            yield session
        except Exception:
            save_failure_artifacts(admin, "失败现场-管理端")
            save_failure_artifacts(mall, "失败现场-商城")
            raise
        finally:
            admin_context.close()
            mall_context.close()
            browser.close()


def login_admin(page: Page) -> None:
    if not ADMIN_ACCOUNT or not ADMIN_PASSWORD:
        import pytest

        pytest.skip("未设置 ADMIN_TEST_ACCOUNT / ADMIN_TEST_PASSWORD")
    page.goto(f"{ADMIN_UI}/login", wait_until="domcontentloaded", timeout=30_000)
    page.locator('input[name="username"]').fill(ADMIN_ACCOUNT)
    page.locator('input[name="password"]').fill(ADMIN_PASSWORD)
    page.locator('button[type="submit"]').click()
    page.wait_for_url("**/dashboard", timeout=20_000)


def login_customer(page: Page, redirect: str = "/") -> None:
    page.goto(f"{MALL_UI}/login?redirect={quote(redirect)}", wait_until="domcontentloaded", timeout=30_000)
    page.get_by_placeholder("请输入 11 位手机号").fill(CUSTOMER_PHONE)
    page.get_by_placeholder("请输入 6 位验证码").fill(CUSTOMER_CODE)
    page.get_by_role("button", name="登录", exact=True).click()
    page.wait_for_url(lambda url: "/login" not in url, timeout=20_000)


@contextmanager
def admin_api() -> Iterator[requests.Session]:
    if not ADMIN_ACCOUNT or not ADMIN_PASSWORD:
        import pytest

        pytest.skip("未设置 ADMIN_TEST_ACCOUNT / ADMIN_TEST_PASSWORD")
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    response = session.post(
        f"{ADMIN_BASE}/auth/login",
        json={"username": ADMIN_ACCOUNT, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    response.raise_for_status()
    body = response.json()
    token = (body.get("data") or {}).get("accessToken")
    if body.get("code") != 0 or not token:
        raise AssertionError(f"管理员登录失败：{body}")
    session.headers["Authorization"] = f"Bearer {token}"
    try:
        yield session
    finally:
        session.close()


def admin_reviews(api: requests.Session, status: str | None = None) -> list[dict]:
    params = {"page": 1, "size": 100}
    if status:
        params["status"] = status
    response = api.get(f"{ADMIN_BASE}/reviews", params=params, timeout=15)
    response.raise_for_status()
    body = response.json()
    assert body.get("code") == 0, body
    return (body.get("data") or {}).get("records") or []


def find_review(api: requests.Session, review_id: int, status: str | None = None) -> dict:
    for record in admin_reviews(api, status=status):
        if str(record.get("id")) == str(review_id):
            return record
    raise AssertionError(f"未找到评价 {review_id}")


def set_reply(api: requests.Session, review_id: int, text: str) -> None:
    response = api.put(f"{ADMIN_BASE}/reviews/{review_id}/reply", json={"reply": text}, timeout=15)
    response.raise_for_status()
    body = response.json()
    assert body.get("code") == 0, body


def expect_toast(page: Page, text: str) -> None:
    expect(page.get_by_text(text, exact=False).first).to_be_visible(timeout=10_000)


def row_for(page: Page, text: str):
    return page.locator("tr", has_text=text).first


def open_review_admin(page: Page, keyword: str = "打工人") -> None:
    """打开评价管理并按商品名过滤，避免 8503 被新评价挤到第二页。"""
    page.goto(f"{ADMIN_UI}/reviews", wait_until="domcontentloaded", timeout=30_000)
    page.get_by_placeholder("商品名 / 会员手机尾号").fill(keyword)
    page.get_by_role("button", name="查询").click()
    expect(page.locator("tbody")).to_contain_text("8503", timeout=15_000)
