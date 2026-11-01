"""知识点 4：契约断言——字段类型、金额、SKU 列表。"""
from decimal import Decimal
from conftest import BASE_URL


def test_product_detail_contract(api):
    response = api.get(f"{BASE_URL}/api/products/101", timeout=10)
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data["spu"]["id"], str)
    assert isinstance(data["spu"]["name"], str)
    assert isinstance(data["skus"], list) and data["skus"]
    for sku in data["skus"]:
        assert isinstance(sku["skuId"], str)
        assert Decimal(str(sku["price"])) > 0
        assert sku["availableStock"] >= 0
