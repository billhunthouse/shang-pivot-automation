"""课件共享 fixture：BASE_URL、会话、唯一会员、认证头。"""
import os
import random
import string
import requests
import pytest

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8086").rstrip("/")


@pytest.fixture(scope="session")
def api():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    yield session
    session.close()


@pytest.fixture
def unique_phone():
    return "139" + "".join(random.choices(string.digits, k=8))


@pytest.fixture
def customer(api, unique_phone):
    response = api.post(f"{BASE_URL}/api/auth/login", json={
        "phone": unique_phone, "code": "123456", "clientType": "web"
    }, timeout=10)
    response.raise_for_status()
    body = response.json()
    assert body["code"] == 0, body
    token = body["data"]["accessToken"]
    return {"phone": unique_phone, "token": token, "headers": {"Authorization": f"Bearer {token}"}}
