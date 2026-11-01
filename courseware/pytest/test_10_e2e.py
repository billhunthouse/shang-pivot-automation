"""知识点 10：API 端到端购买旅程。"""
import uuid
from conftest import BASE_URL


def test_purchase_flow(api, customer):
    headers = customer["headers"]
    address = api.post(f"{BASE_URL}/api/addresses", headers=headers, json={
        "name": "课件用户", "phone": customer["phone"],
        "province": "北京市", "city": "北京市", "district": "朝阳区",
        "detail": "课件路 1 号", "isDefault": True,
    }, timeout=10).json()
    assert address["code"] == 0
    address_id = address["data"]

    order = api.post(f"{BASE_URL}/api/orders", headers=headers, json={
        "addressId": address_id, "skuId": "10026", "quantity": 1,
        "idempotentKey": f"courseware-{uuid.uuid4()}",
    }, timeout=10).json()
    assert order["code"] == 0
    order_id = order["data"]["orderId"]
    assert order["data"]["status"] == "PENDING_PAY"

    paid = api.post(f"{BASE_URL}/api/payment/sandbox", headers=headers,
                    json={"orderId": order_id}, timeout=10).json()
    assert paid["code"] == 0
    assert paid["data"]["status"] == "PENDING_SHIP"

    detail = api.get(f"{BASE_URL}/api/orders/{order_id}", headers=headers, timeout=10).json()
    assert detail["data"]["order"]["status"] == "PENDING_SHIP"
