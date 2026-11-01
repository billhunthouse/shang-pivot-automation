"""知识点 7：Allure step 与附件。"""
import allure
from conftest import BASE_URL


@allure.epic("尚品汇")
@allure.feature("商品")
@allure.story("首页运营位")
@allure.severity(allure.severity_level.CRITICAL)
def test_home_with_allure(api):
    with allure.step("请求首页"):
        response = api.get(f"{BASE_URL}/api/home", timeout=10)
        allure.attach(response.text, "response.json", allure.attachment_type.JSON)
    with allure.step("断言业务码与商品流"):
        body = response.json()
        assert body["code"] == 0
        assert body["data"]["feed"]
