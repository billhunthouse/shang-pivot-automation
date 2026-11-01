"""知识点 5：marker 分层执行（-m smoke / -m negative）。"""
import pytest
from conftest import BASE_URL


@pytest.mark.smoke
def test_categories_public(api):
    body = api.get(f"{BASE_URL}/api/categories", timeout=10).json()
    assert body["code"] == 0
    assert isinstance(body["data"], list)


@pytest.mark.negative
def test_cart_requires_token(api):
    response = api.get(f"{BASE_URL}/api/cart", timeout=10)
    assert response.status_code == 401
