"""跨页面业务冒烟：搜索、商品筛选、库存筛选、售后详情。"""
from __future__ import annotations

import re

import allure
import pytest
from playwright.sync_api import expect

from .ui_support import ADMIN_UI, MALL_UI, login_customer, row_for, step

pytestmark = [pytest.mark.ui, pytest.mark.smoke, pytest.mark.regression]


@allure.epic("尚品汇 · UI 自动化")
@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("业务冒烟")
@allure.feature("商城浏览")
@allure.story("搜索到详情")
@allure.title("UI-MALL-001 首页搜索 iPhone 并进入商品详情")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("UI", "P0", "mall", "search")
def test_search_to_product_detail(smoke_pages):
    page = smoke_pages["guest"]
    with step(page, "打开商城首页"):
        page.goto(f"{MALL_UI}/", wait_until="domcontentloaded", timeout=30_000)
        expect(page.get_by_placeholder("搜索商品名称 / 副标题")).to_be_visible()

    with step(page, "搜索 iPhone"):
        page.get_by_placeholder("搜索商品名称 / 副标题").fill("iPhone")
        page.get_by_role("button", name="搜索").click()
        page.wait_for_url("**/search?q=iPhone", timeout=15_000)
        expect(page.locator("body")).to_contain_text("iPhone", timeout=15_000)

    with step(page, "进入商品详情"):
        page.locator('a[href*="/product/"]').first.click()
        page.wait_for_url("**/product/**", timeout=15_000)
        expect(page.locator("body")).to_contain_text("iPhone", timeout=15_000)


@allure.epic("尚品汇 · UI 自动化")
@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("业务冒烟")
@allure.feature("购物车")
@allure.story("加购与删除")
@allure.title("UI-MALL-002 商品加入购物车并从购物车删除")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("UI", "P0", "mall", "cart")
def test_add_to_cart_and_remove(smoke_pages):
    page = smoke_pages["customer"]
    with step(page, "打开商品详情"):
        page.goto(f"{MALL_UI}/product/111", wait_until="domcontentloaded", timeout=30_000)
        expect(page.get_by_role("heading", name="vivo X100")).to_be_visible()

    with step(page, "加入购物车"):
        page.get_by_role("button", name="加入购物车", exact=True).first.click()
        popup = page.locator(".pop-panel", has_text="选择规格")
        expect(popup).to_be_visible()
        popup.get_by_role("button", name="加入购物车", exact=True).click()
        expect(page.get_by_text("已加入购物车")).to_be_visible(timeout=15_000)
        page.get_by_role("button", name="去购物车结算").click()
        page.wait_for_url("**/cart", timeout=15_000)

    with step(page, "购物车存在该商品"):
        item = page.locator(".cart-item", has_text="vivo X100").first
        expect(item).to_be_visible(timeout=15_000)

    with step(page, "删除购物车商品"):
        item.get_by_role("button", name="删除").click()
        dialog = page.locator(".pop-panel", has_text="删除商品")
        expect(dialog).to_be_visible()
        dialog.get_by_role("button", name="删除", exact=True).click()
        expect(page.locator(".cart-item", has_text="vivo X100")).to_have_count(0)


@allure.epic("尚品汇 · UI 自动化")
@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("业务冒烟")
@allure.feature("响应式布局")
@allure.story("H5 关键页面")
@allure.title("UI-MOBILE-001 390×844 视口下首页/商品/购物车/订单可访问")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("UI", "P0", "mobile", "h5")
def test_mobile_key_pages(smoke_pages):
    context = smoke_pages["browser"].new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
    )
    page = context.new_page()
    try:
        login_customer(page, redirect="/")
        for path, text in [
            ("/", "为你推荐"),
            ("/product/111", "vivo X100"),
            ("/cart", "购物车"),
            ("/orders", "我的订单"),
        ]:
            with step(page, f"H5 访问 {path}"):
                page.goto(f"{MALL_UI}{path}", wait_until="domcontentloaded", timeout=30_000)
                expect(page.locator("body")).to_contain_text(text, timeout=15_000)
    finally:
        context.close()


@allure.epic("尚品汇 · UI 自动化")
@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("业务冒烟")
@allure.feature("商品管理")
@allure.story("商品查询")
@allure.title("UI-ADMIN-001 商品列表按关键词查询")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("UI", "P1", "admin", "product")
def test_admin_product_search(smoke_pages):
    page = smoke_pages["admin"]
    with step(page, "打开商品列表"):
        page.goto(f"{ADMIN_UI}/products", wait_until="domcontentloaded", timeout=30_000)
        expect(page.get_by_text("商品列表").first).to_be_visible()

    with step(page, "按关键词查询 vivo"):
        page.get_by_placeholder("商品名称 / 编码").fill("vivo")
        page.get_by_role("button", name="查询").click()
        expect(page.locator("tbody")).to_contain_text("vivo", timeout=15_000)


@allure.epic("尚品汇 · UI 自动化")
@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("业务冒烟")
@allure.feature("库存管理")
@allure.story("低库存筛选")
@allure.title("UI-ADMIN-002 库存管理切换到低库存/关注视图")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("UI", "P1", "admin", "inventory")
def test_admin_inventory_low_stock(smoke_pages):
    page = smoke_pages["admin"]
    with step(page, "打开库存管理"):
        page.goto(f"{ADMIN_UI}/inventory", wait_until="domcontentloaded", timeout=30_000)
        expect(page.get_by_text("库存管理").first).to_be_visible()

    with step(page, "切换到低库存/关注"):
        page.locator(".tab", has_text="低库存").click()
        expect(page.locator("body")).to_contain_text("低库存", timeout=15_000)


@allure.epic("尚品汇 · UI 自动化")
@allure.parent_suite("尚品汇 UI 自动化")
@allure.suite("业务冒烟")
@allure.feature("售后管理")
@allure.story("售后详情")
@allure.title("UI-ADMIN-003 售后列表打开详情抽屉")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("UI", "P1", "admin", "aftersales")
def test_admin_aftersale_detail(smoke_pages):
    page = smoke_pages["admin"]
    with step(page, "打开售后管理"):
        page.goto(f"{ADMIN_UI}/aftersales", wait_until="domcontentloaded", timeout=30_000)
        expect(page.get_by_text("售后管理").first).to_be_visible()

    with step(page, "打开售后详情"):
        row_for(page, "AS202609140101").get_by_role("button", name=re.compile("审核|详情")).click()
        expect(page.get_by_text("售后详情").last).to_be_visible(timeout=15_000)
