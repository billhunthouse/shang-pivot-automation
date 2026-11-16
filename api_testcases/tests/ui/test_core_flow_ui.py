"""核心交易链路 UI 自动化：立即购买 → 支付 → 管理员发货 → 确认收货 → 评价 → 商家回复。"""
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
    login_admin,
    login_customer,
    row_for,
    step,
)

pytestmark = [pytest.mark.ui, pytest.mark.e2e, pytest.mark.regression]


@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("核心交易链路")
@allure.epic("尚品汇 · UI 自动化")
@allure.feature("核心交易链路")
@allure.story("下单到评价闭环")
@allure.title("UI-CORE-001 顾客购买→管理员发货→确认收货→评价→商家回复")
@allure.severity(allure.severity_level.BLOCKER)
@allure.tag("UI", "P0", "e2e", "order", "review")
def test_purchase_delivery_review_loop(ui):
    stamp = int(time.time())
    review_content = f"UI自动化评价-{stamp}"
    merchant_reply = f"UI自动化商家回复-{stamp}"

    with step(ui.mall, "顾客登录并打开商品详情"):
        login_customer(ui.mall, redirect="/product/111")
        expect(ui.mall.get_by_role("heading", name="vivo X100")).to_be_visible()
        expect(ui.mall.get_by_text("有货")).to_be_visible()

    with step(ui.mall, "选择规格并立即购买"):
        ui.mall.get_by_role("button", name="立即购买", exact=True).first.click()
        popup = ui.mall.locator(".pop-panel", has_text="选择规格")
        expect(popup).to_be_visible()
        popup.get_by_role("button", name="立即购买", exact=True).click()

    with step(ui.mall, "确认下单信息"):
        confirm = ui.mall.locator(".pop-panel", has_text="确认下单信息")
        expect(confirm).to_be_visible()
        confirm.get_by_role("button", name="去确认订单").click()
        ui.mall.wait_for_url("**/checkout**", timeout=20_000)

    with step(ui.mall, "提交订单"):
        expect(ui.mall.get_by_text("收货地址")).to_be_visible()
        expect(ui.mall.get_by_text("张三").first).to_be_visible()
        ui.mall.get_by_role("button", name="提交订单").click()
        dialog = ui.mall.locator(".pop-panel", has_text="确认提交订单")
        expect(dialog).to_be_visible()
        dialog.get_by_role("button", name="确认提交").click()
        ui.mall.wait_for_url("**/pay/**", timeout=20_000)

    with step(ui.mall, "沙箱支付成功"):
        expect(ui.mall.get_by_text("支付成功")).to_be_visible(timeout=20_000)
        ui.mall.get_by_role("button", name="查看支付结果").click()
        expect(ui.mall.get_by_text("支付结果")).to_be_visible()
        ui.mall.get_by_role("button", name="查看订单").click()
        ui.mall.wait_for_url("**/orders/**", timeout=20_000)

    with step(ui.mall, "记录订单号并确认待发货"):
        expect(ui.mall.get_by_text(re.compile(r"订单号\s*O\d+"))).to_be_visible(timeout=15_000)
        body = ui.mall.locator("body").inner_text()
        match = re.search(r"O\d{10,}", body)
        assert match, "订单详情未展示订单号"
        order_no = match.group(0)
        order_id = ui.mall.url.rstrip("/").split("/")[-1]
        assert order_id.isdigit()
        expect(ui.mall.get_by_text("状态 PENDING_SHIP")).to_be_visible()
        allure.attach(
            f"orderNo={order_no}\norderId={order_id}",
            name="订单信息.txt",
            attachment_type=allure.attachment_type.TEXT,
        )

    with step(ui.admin, "管理员登录并查询订单"):
        login_admin(ui.admin)
        ui.admin.goto(f"{ADMIN_UI}/orders", wait_until="domcontentloaded", timeout=30_000)
        ui.admin.get_by_placeholder("订单号").fill(order_no)
        ui.admin.get_by_role("button", name="查询").click()
        row = row_for(ui.admin, order_no)
        expect(row).to_be_visible(timeout=15_000)
        expect(row).to_contain_text("待发货")

    with step(ui.admin, "录入运单号并发货"):
        row.get_by_role("button", name="发货").click()
        dialog = ui.admin.locator(".modal-panel", has_text="订单发货")
        expect(dialog).to_be_visible()
        dialog.get_by_placeholder("请录入运单号").fill(f"SF-UI-{stamp}")
        dialog.get_by_role("button", name="确认发货").click()
        expect(dialog).to_have_count(0)
        expect_toast(ui.admin, "已确认发货")

    with step(ui.mall, "顾客刷新订单并确认收货"):
        ui.mall.reload(wait_until="domcontentloaded")
        expect(ui.mall.get_by_text("状态 PENDING_RECEIVE")).to_be_visible(timeout=15_000)
        ui.mall.get_by_role("button", name="确认收货").click()
        ui.mall.locator(".van-dialog__confirm").click()
        expect_toast(ui.mall, "已确认收货")
        expect(ui.mall.get_by_text("状态 COMPLETED")).to_be_visible(timeout=15_000)

    with step(ui.mall, "提交 5 星评价"):
        ui.mall.get_by_role("button", name="评价", exact=True).click()
        dialog = ui.mall.locator(".pop-panel", has_text="发表评价")
        expect(dialog).to_be_visible()
        dialog.get_by_role("button", name="5 分", exact=True).click()
        dialog.get_by_placeholder("说说使用感受，最多 500 字").fill(review_content)
        dialog.get_by_role("button", name="提交评价").click()
        expect_toast(ui.mall, "评价成功")

    with step(ui.mall, "C 端商品详情出现新评价"):
        ui.mall.goto(f"{MALL_UI}/product/111", wait_until="domcontentloaded", timeout=30_000)
        expect(ui.mall.get_by_text(review_content)).to_be_visible(timeout=15_000)

    with step(ui.admin, "管理员回复新评价"):
        ui.admin.goto(f"{ADMIN_UI}/reviews", wait_until="domcontentloaded", timeout=30_000)
        row = row_for(ui.admin, review_content[:12])
        expect(row).to_be_visible(timeout=15_000)
        row.get_by_role("button", name="回复").click()
        dialog = ui.admin.locator(".modal-panel")
        expect(dialog).to_be_visible()
        dialog.locator("textarea").fill(merchant_reply)
        dialog.get_by_role("button", name="保存回复").click()
        expect(dialog).to_have_count(0)
        expect_toast(ui.admin, "回复已保存")

    with step(ui.mall, "C 端商品详情展示商家回复"):
        ui.mall.goto(f"{MALL_UI}/product/111", wait_until="domcontentloaded", timeout=30_000)
        expect(ui.mall.get_by_text(merchant_reply)).to_be_visible(timeout=15_000)
