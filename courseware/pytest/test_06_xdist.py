"""知识点 6：xdist 并行；每个用例只读、无共享状态。"""
import pytest
from conftest import BASE_URL

PRODUCT_IDS = ["101", "102", "103", "104", "121", "162"]


@pytest.mark.parametrize("spu_id", PRODUCT_IDS)
def test_product_detail_read_only(api, spu_id):
    response = api.get(f"{BASE_URL}/api/products/{spu_id}", timeout=10)
    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert response.json()["data"]["spu"]["id"] == spu_id
