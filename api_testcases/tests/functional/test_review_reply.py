"""评价商家回复：API 契约 + 业务闭环。

运行前设置：
  ADMIN_BASE_URL=http://127.0.0.1:8086/admin
  MALL_BASE_URL=http://127.0.0.1:8086
  ADMIN_TEST_ACCOUNT=admin
  ADMIN_TEST_PASSWORD=...
"""
from __future__ import annotations

import os
import time

import allure
import pytest
import requests

ADMIN_BASE = os.getenv("ADMIN_BASE_URL", "http://127.0.0.1:8086/admin").rstrip("/")
MALL_BASE = os.getenv("MALL_BASE_URL", "http://127.0.0.1:8086").rstrip("/")
ADMIN_ACCOUNT = os.getenv("ADMIN_TEST_ACCOUNT", "")
ADMIN_PASSWORD = os.getenv("ADMIN_TEST_PASSWORD", "")


def _session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    return session


def _business(response: requests.Response) -> dict:
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, dict), body
    return body


@pytest.fixture(scope="module")
def admin_token() -> str:
    if not ADMIN_ACCOUNT or not ADMIN_PASSWORD:
        pytest.skip("未设置 ADMIN_TEST_ACCOUNT / ADMIN_TEST_PASSWORD")
    with _session() as session:
        response = session.post(
            f"{ADMIN_BASE}/auth/login",
            json={"username": ADMIN_ACCOUNT, "password": ADMIN_PASSWORD},
        )
        body = _business(response)
        assert body.get("code") == 0, body
        token = (body.get("data") or {}).get("accessToken")
        assert token
        return token


@pytest.fixture(scope="module")
def admin_client(admin_token: str):
    with _session() as session:
        session.headers["Authorization"] = f"Bearer {admin_token}"
        yield session


@pytest.fixture(scope="module")
def visible_review(admin_client: requests.Session) -> dict:
    response = admin_client.get(f"{ADMIN_BASE}/reviews", params={"page": 1, "size": 20, "status": "VISIBLE"})
    body = _business(response)
    assert body.get("code") == 0, body
    records = (body.get("data") or {}).get("records") or []
    assert records, "没有可见评价，无法执行回复测试"
    return records[0]


@allure.epic("尚品汇 · 评价商家回复")
@allure.feature("评价管理")
class TestReviewReply:
    @allure.story("回复成功")
    @allure.title("API-REPLY-001 管理员回复可见评价，C 端商品详情景展示")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_reply_success_and_public_visibility(self, admin_client, visible_review):
        reply = f"自动化测试商家回复-{int(time.time())}"
        with allure.step("管理端提交回复"):
            response = admin_client.put(f"{ADMIN_BASE}/reviews/{visible_review['id']}/reply", json={"reply": reply})
            body = _business(response)
            assert body.get("code") == 0, body

        with allure.step("管理端列表回查回复"):
            list_response = admin_client.get(f"{ADMIN_BASE}/reviews", params={"page": 1, "size": 50})
            records = (_business(list_response).get("data") or {}).get("records") or []
            matched = next((item for item in records if str(item.get("id")) == str(visible_review["id"])), None)
            assert matched is not None
            assert matched.get("merchantReply") == reply
            assert matched.get("repliedAt")

        with allure.step("C 端评价列表可见"):
            public_response = requests.get(
                f"{MALL_BASE}/api/products/{visible_review['spuId']}/reviews",
                params={"page": 1, "size": 20},
                timeout=10,
            )
            assert public_response.status_code == 200
            public_body = public_response.json()
            assert public_body.get("code") == 0
            public_records = (public_body.get("data") or {}).get("records") or []
            public_matched = next((item for item in public_records if str(item.get("id")) == str(visible_review["id"])), None)
            assert public_matched is not None
            assert public_matched.get("merchantReply") == reply

        with allure.step("商品详情 reviewsPreview 可见"):
            detail_response = requests.get(f"{MALL_BASE}/api/products/{visible_review['spuId']}", timeout=10)
            assert detail_response.status_code == 200
            detail_body = detail_response.json()
            preview = (detail_body.get("data") or {}).get("reviewsPreview") or []
            preview_matched = next((item for item in preview if str(item.get("id")) == str(visible_review["id"])), None)
            assert preview_matched is not None
            assert preview_matched.get("merchantReply") == reply

    @allure.story("重复回复")
    @allure.title("API-REPLY-006 重复回复覆盖上一条")
    def test_reply_overwrites_previous(self, admin_client, visible_review):
        first = "第一次商家回复"
        second = "第二次商家回复-覆盖验证"
        for text in (first, second):
            body = _business(admin_client.put(
                f"{ADMIN_BASE}/reviews/{visible_review['id']}/reply", json={"reply": text}
            ))
            assert body.get("code") == 0, body
        body = _business(admin_client.get(f"{ADMIN_BASE}/reviews", params={"page": 1, "size": 50}))
        records = (body.get("data") or {}).get("records") or []
        matched = next((item for item in records if str(item.get("id")) == str(visible_review["id"])), None)
        assert matched and matched.get("merchantReply") == second

    @allure.story("参数校验")
    @allure.title("API-REPLY-003 空回复被拒绝")
    def test_reply_blank_rejected(self, admin_client, visible_review):
        body = _business(admin_client.put(
            f"{ADMIN_BASE}/reviews/{visible_review['id']}/reply", json={"reply": "   "}
        ))
        assert body.get("code") == 40000, body
        assert "不能为空" in (body.get("msg") or "")

    @allure.story("参数校验")
    @allure.title("API-REPLY-004 超过 500 字被拒绝")
    def test_reply_too_long_rejected(self, admin_client, visible_review):
        body = _business(admin_client.put(
            f"{ADMIN_BASE}/reviews/{visible_review['id']}/reply", json={"reply": "测" * 501}
        ))
        assert body.get("code") == 40000, body
        assert "500" in (body.get("msg") or "")

    @allure.story("资源不存在")
    @allure.title("API-REPLY-005 不存在的评价返回 40400")
    def test_reply_missing_review(self, admin_client):
        body = _business(admin_client.put(
            f"{ADMIN_BASE}/reviews/999999999/reply", json={"reply": "测试"}
        ))
        assert body.get("code") == 40400, body

    @allure.story("隐藏评价")
    @allure.title("API-REPLY-007 隐藏评价可回复，但 C 端不展示")
    def test_reply_hidden_review_not_public(self, admin_client):
        listing = _business(admin_client.get(f"{ADMIN_BASE}/reviews", params={"page": 1, "size": 50, "status": "HIDDEN"}))
        records = (listing.get("data") or {}).get("records") or []
        if not records:
            pytest.skip("没有隐藏评价，跳过")
        target = records[0]
        reply = "隐藏评价的商家回复"
        assert _business(admin_client.put(f"{ADMIN_BASE}/reviews/{target['id']}/reply", json={"reply": reply})).get("code") == 0
        public = requests.get(f"{MALL_BASE}/api/products/{target['spuId']}/reviews", params={"page": 1, "size": 50}, timeout=10)
        public_records = (public.json().get("data") or {}).get("records") or []
        assert all(str(item.get("id")) != str(target["id"]) for item in public_records)

    @allure.story("鉴权")
    @allure.title("API-REPLY-002 未登录回复被拒绝")
    def test_reply_requires_auth(self, visible_review):
        with _session() as session:
            response = session.put(
                f"{ADMIN_BASE}/reviews/{visible_review['id']}/reply", json={"reply": "未登录测试"}
            )
            assert response.status_code == 401
