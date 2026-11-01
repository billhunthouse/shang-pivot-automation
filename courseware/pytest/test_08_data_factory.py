"""知识点 8：唯一数据 + 精确清理。"""
from conftest import BASE_URL


def test_add_and_remove_cart_item(api, customer):
    created = api.post(f"{BASE_URL}/api/cart/items", headers=customer["headers"],
                       json={"skuId": "10001", "quantity": 1}, timeout=10).json()
    assert created["code"] == 0
    cart_item_id = created["data"]["cartItemId"]
    try:
        cart = api.get(f"{BASE_URL}/api/cart", headers=customer["headers"], timeout=10).json()
        item = next(i for i in cart["data"]["items"] if i["cartItemId"] == cart_item_id)
        assert item["quantity"] == 1
        assert item["selected"] is True
    finally:
        api.delete(f"{BASE_URL}/api/cart/items/{cart_item_id}", headers=customer["headers"], timeout=10)
