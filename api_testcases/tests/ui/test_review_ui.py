"""评价商家回复 UI 自动化：列表、弹窗、校验、跨端展示、隐藏评价与 XSS。

所有用例默认跳过；需要：
  RUN_UI=1
  ADMIN_UI_URL / MALL_UI_URL
  ADMIN_TEST_ACCOUNT / ADMIN_TEST_PASSWORD
  MALL_TEST_PHONE / MALL_TEST_CODE
"""
from __future__ import annotations

import re
import time

import allure
import pytest
from playwright.sync_api import expect

from .ui_support import (
    ADMIN_UI,
    MALL_UI,
    expect_toast,
    find_review,
    login_admin,
    login_customer,
    open_review_admin,
    row_for,
    set_reply,
    step,
)

pytestmark = [pytest.mark.ui, pytest.mark.regression]


@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("评价商家回复")
@allure.epic("尚品汇 · UI 自动化")
@allure.feature("评价管理")
@allure.story("评价列表")
@allure.title("UI-REVIEW-001 评价列表展示商家回复列与回复操作")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("UI", "P1", "review")
def test_review_list_shows_reply_column(ui, review_target):
    with step(ui.admin, "管理员登录"):
        login_admin(ui.admin)

    with step(ui.admin, "打开评价管理并筛选罗技"):
        open_review_admin(ui.admin)
        expect(ui.admin.get_by_text("评价管理").first).to_be_visible()

    with step(ui.admin, "检查商家回复列"):
        headers = ui.admin.locator("thead th").all_inner_texts()
        assert "商家回复" in headers
        row = row_for(ui.admin, str(review_target["id"]))
        expect(row).to_be_visible()
        expect(row.locator(".reply-cell")).not_to_have_text("—")
        expect(row.get_by_role("button", name=re.compile("回复"))).to_be_visible()


@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("评价商家回复")
@allure.epic("尚品汇 · UI 自动化")
@allure.feature("评价管理")
@allure.story("回复弹窗")
@allure.title("UI-REVIEW-002 回复弹窗展示评价摘要、原回复与字数提示")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("UI", "P1", "review")
def test_reply_dialog_shows_summary_and_counter(ui, review_target):
    with step(ui.admin, "管理员登录"):
        login_admin(ui.admin)
    with step(ui.admin, "打开评价管理并筛选罗技"):
        open_review_admin(ui.admin)
        row_for(ui.admin, str(review_target["id"])).wait_for(state="visible", timeout=15_000)

    with step(ui.admin, "打开回复弹窗"):
        row_for(ui.admin, str(review_target["id"])).get_by_role("button", name=re.compile("回复")).click()
        dialog = ui.admin.locator(".modal-panel")
        expect(dialog).to_be_visible()
        expect(dialog.locator(".modal-title")).to_have_text(re.compile("回复评价|修改商家回复"))
        expect(dialog.locator(".reply-summary")).to_contain_text("商品")
        expect(dialog.locator(".reply-summary")).to_contain_text("评价")
        expect(dialog.locator("textarea")).to_be_visible()
        expect(dialog.locator(".hint")).to_contain_text("/ 500")


@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("评价商家回复")
@allure.epic("尚品汇 · UI 自动化")
@allure.feature("评价管理")
@allure.story("表单校验")
@allure.title("UI-REVIEW-003 空回复在弹窗内联提示，不关闭弹窗")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("UI", "P1", "review", "negative")
def test_blank_reply_inline_validation(ui, review_target):
    with step(ui.admin, "管理员登录并打开评价管理"):
        login_admin(ui.admin)
        open_review_admin(ui.admin)
        row = row_for(ui.admin, str(review_target["id"]))
        row.wait_for(state="visible", timeout=15_000)
        row.get_by_role("button", name=re.compile("回复")).click()

    with step(ui.admin, "清空回复并提交"):
        dialog = ui.admin.locator(".modal-panel")
        dialog.locator("textarea").fill("")
        dialog.get_by_role("button", name="保存回复").click()

    with step(ui.admin, "断言内联错误"):
        expect(dialog.locator(".error-text")).to_have_text("回复内容不能为空")
        expect(dialog).to_be_visible()


@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("评价商家回复")
@allure.epic("尚品汇 · UI 自动化")
@allure.feature("评价管理")
@allure.story("表单校验")
@allure.title("UI-REVIEW-004 500 字边界保存成功")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("UI", "P2", "review", "boundary")
def test_reply_500_chars_saved(ui, review_target):
    text = "测" * 500
    with step(ui.admin, "管理员登录并打开评价管理"):
        login_admin(ui.admin)
        open_review_admin(ui.admin)
        row = row_for(ui.admin, str(review_target["id"]))
        row.wait_for(state="visible", timeout=15_000)
        row.get_by_role("button", name=re.compile("回复")).click()

    with step(ui.admin, "输入 500 字并检查计数"):
        dialog = ui.admin.locator(".modal-panel")
        dialog.locator("textarea").fill(text)
        expect(dialog.locator(".hint")).to_have_text("500 / 500")

    with step(ui.admin, "保存回复"):
        dialog.get_by_role("button", name="保存回复").click()
        expect(dialog).to_have_count(0)
        expect_toast(ui.admin, "回复已保存")

    with step(ui.admin, "列表回查 500 字回复"):
        row_for(ui.admin, str(review_target["id"])).locator(".reply-cell").wait_for(state="visible")


@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("评价商家回复")
@allure.epic("尚品汇 · UI 自动化")
@allure.feature("评价管理")
@allure.story("修改回复")
@allure.title("UI-REVIEW-005 重复回复覆盖前一次内容")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("UI", "P1", "review")
def test_reply_overwrites_previous(ui, review_target):
    first = "覆盖验证-第一次"
    second = "覆盖验证-第二次"
    with step(ui.admin, "管理员登录并打开评价管理"):
        login_admin(ui.admin)
        open_review_admin(ui.admin)
        row = row_for(ui.admin, str(review_target["id"]))
        row.wait_for(state="visible", timeout=15_000)
        row.get_by_role("button", name=re.compile("回复")).click()

    with step(ui.admin, "保存第一次回复"):
        dialog = ui.admin.locator(".modal-panel")
        dialog.locator("textarea").fill(first)
        dialog.get_by_role("button", name="保存回复").click()
        expect(dialog).to_have_count(0)

    with step(ui.admin, "再次打开并检查原回复回填"):
        row = row_for(ui.admin, str(review_target["id"]))
        row.get_by_role("button", name="修改回复").click()
        dialog = ui.admin.locator(".modal-panel")
        expect(dialog.locator("textarea")).to_have_value(first)

    with step(ui.admin, "保存第二次回复"):
        dialog.locator("textarea").fill(second)
        dialog.get_by_role("button", name="保存回复").click()
        expect(dialog).to_have_count(0)

    with step(ui.admin, "列表显示第二次内容"):
        expect(row_for(ui.admin, str(review_target["id"])).locator(".reply-cell")).to_contain_text(second)


@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("评价商家回复")
@allure.epic("尚品汇 · UI 自动化")
@allure.feature("评价展示")
@allure.story("C 端展示")
@allure.title("UI-REVIEW-006 有回复展示、无回复不展示空块")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("UI", "P1", "review", "cross-end")
def test_c_end_shows_reply_only_when_present(ui, review_api, review_target):
    current = find_review(review_api, review_target["id"], status="VISIBLE")
    current_reply = current.get("merchantReply") or ""
    if not current_reply:
        set_reply(review_api, review_target["id"], "UI 跨端展示回复")
        current_reply = "UI 跨端展示回复"

    with step(ui.mall, "打开有回复的商品详情"):
        ui.mall.goto(f"{MALL_UI}/product/127", wait_until="domcontentloaded", timeout=30_000)
        expect(ui.mall.locator(".reviews")).to_be_visible()
        expect(ui.mall.locator(".merchant-reply")).to_contain_text(current_reply)

    with step(ui.mall, "打开无回复的商品详情"):
        ui.mall.goto(f"{MALL_UI}/product/162", wait_until="domcontentloaded", timeout=30_000)
        expect(ui.mall.locator(".reviews")).to_be_visible()
        expect(ui.mall.locator(".merchant-reply")).to_have_count(0)


@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("评价商家回复")
@allure.epic("尚品汇 · UI 自动化")
@allure.feature("评价管理")
@allure.story("隐藏评价")
@allure.title("UI-REVIEW-007 隐藏评价在管理端可见、C 端不展示")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("UI", "P2", "review", "negative")
def test_hidden_review_not_public(ui):
    with step(ui.admin, "管理员登录并查看已隐藏评价"):
        login_admin(ui.admin)
        ui.admin.goto(f"{ADMIN_UI}/reviews", wait_until="domcontentloaded", timeout=30_000)
        ui.admin.locator(".tab", has_text="已隐藏").click()
        row = row_for(ui.admin, "8504")
        expect(row).to_be_visible()
        expect(row).to_contain_text("隐藏")

    with step(ui.mall, "C 端商品详情不展示隐藏评价"):
        ui.mall.goto(f"{MALL_UI}/product/101", wait_until="domcontentloaded", timeout=30_000)
        expect(ui.mall.locator(".reviews")).to_have_count(0)
        expect(ui.mall.get_by_text("隐藏评价的商家回复")).to_have_count(0)


@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("评价商家回复")
@allure.epic("尚品汇 · UI 自动化")
@allure.feature("评价管理")
@allure.story("权限")
@allure.title("UI-REVIEW-008 未登录访问评价管理被重定向到登录页")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("UI", "P1", "review", "auth")
def test_review_admin_requires_login(ui):
    context = ui.browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    try:
        with step(page, "未登录直接访问评价管理"):
            page.goto(f"{ADMIN_UI}/reviews", wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_url("**/login**", timeout=15_000)
            expect(page.locator('input[name="username"]')).to_be_visible()
    finally:
        context.close()


@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("评价商家回复")
@allure.epic("尚品汇 · UI 自动化")
@allure.feature("评价展示")
@allure.story("安全")
@allure.title("UI-REVIEW-009 商家回复中的 HTML 按文本渲染，不执行脚本")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("UI", "P2", "review", "security")
def test_reply_html_is_escaped(ui, review_api, review_target):
    payload = f'<img src=x onerror="window.__xssReached=1">XSS-{int(time.time())}'
    set_reply(review_api, review_target["id"], payload)

    with step(ui.mall, "打开商品详情查看回复"):
        ui.mall.goto(f"{MALL_UI}/product/127", wait_until="domcontentloaded", timeout=30_000)
        reply = ui.mall.locator(".merchant-reply")
        expect(reply).to_contain_text("<img")
        assert ui.mall.locator(".merchant-reply img").count() == 0
        assert ui.mall.evaluate("window.__xssReached") is None


@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("评价商家回复")
@allure.epic("尚品汇 · UI 自动化")
@allure.feature("订单评价")
@allure.story("评价入口")
@allure.title("UI-REVIEW-010 已完成订单显示已评价状态，不重复展示评价按钮")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("UI", "P1", "review", "order")
def test_completed_order_shows_reviewed_state(ui):
    with step(ui.mall, "顾客登录"):
        login_customer(ui.mall, redirect="/orders/104")

    with step(ui.mall, "打开已完成订单详情"):
        expect(ui.mall.get_by_text("状态 COMPLETED")).to_be_visible()
        expect(ui.mall.get_by_text("AirPods Pro 2")).to_be_visible()

    with step(ui.mall, "检查已评价状态"):
        expect(ui.mall.get_by_text("已评价 · 提交后不可修改")).to_be_visible()
        item = ui.mall.locator(".item", has_text="AirPods Pro 2")
        expect(item.get_by_role("button", name="评价")).to_have_count(0)
