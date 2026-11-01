"""知识点 2：fixture 分层、登录复用、请求头注入。"""
from conftest import BASE_URL


def test_customer_profile(api, customer):
    response = api.get(f"{BASE_URL}/api/me", headers=customer["headers"], timeout=10)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "NORMAL"


def test_another_customer_is_isolated(api, customer, unique_phone):
    login = api.post(f"{BASE_URL}/api/auth/login", json={
        "phone": unique_phone, "code": "123456", "clientType": "web"
    }, timeout=10).json()
    other = login["data"]["accessToken"]
    me = api.get(f"{BASE_URL}/api/me", headers={"Authorization": f"Bearer {other}"}, timeout=10).json()
    assert me["data"]["phone"].endswith(unique_phone[-4:])
    assert me["data"]["phone"] != customer["phone"]
