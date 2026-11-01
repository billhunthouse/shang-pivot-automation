"""知识点 3：参数化，用同一逻辑覆盖命中/未命中。"""
import pytest
from conftest import BASE_URL


@pytest.mark.parametrize("keyword,expect_hit", [
    ("iPhone", True),
    ("不存在的商品xyz", False),
])
def test_search(api, keyword, expect_hit):
    response = api.get(f"{BASE_URL}/api/search", params={"q": keyword, "page": 1, "size": 10}, timeout=10)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    total = int(body["data"]["total"])  # 后端 Long 序列化为字符串
    if expect_hit:
        assert total > 0
    else:
        assert total == 0
