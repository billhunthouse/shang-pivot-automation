"""知识点 1：最小可运行用例、断言 HTTP 与业务码。"""
from conftest import BASE_URL


def test_home_is_healthy(api):
    response = api.get(f"{BASE_URL}/api/home", timeout=10)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert len(body["data"]["feed"]) > 0
    assert len(body["data"]["slots"]) > 0
