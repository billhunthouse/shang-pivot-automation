# Pytest 自动化测试课件（尚品汇电商项目）

> 目标：从“会写 assert”到“能进 CI 的测试资产”。
> 所有案例都可直接运行，项目接口为本地尚品汇后端 `http://127.0.0.1:8086`。
> 脚本目录：[`courseware/pytest/`](pytest/)

## 0. 环境与运行

```bash
# 1. 启动被测项目
cd /Users/imac/Desktop/电商自动化测试/shang-pivot-master
bash automation/scripts/start-local.sh

# 2. 安装课件依赖（复用项目 venv）
cd courseware/pytest
../../pytest_automation/.venv/bin/pip install -r requirements.txt

# 3. 全量运行
../../pytest_automation/.venv/bin/python -m pytest -q
# 预期：22 passed
```

目录：

```text
courseware/pytest/
├── conftest.py              # BASE_URL、api、unique_phone、customer fixture
├── pytest.ini               # marker 定义
├── test_01_basic.py         # 最小用例
├── test_02_fixtures.py      # fixture 分层
├── test_03_parametrize.py   # 参数化
├── test_04_contract.py      # 契约断言
├── test_05_markers.py       # marker 分层
├── test_06_xdist.py         # 并行
├── test_07_allure.py        # Allure
├── test_08_data_factory.py  # 数据工厂与清理
├── test_09_mock.py          # mock 外部依赖
├── test_10_e2e.py           # 端到端购买
└── test_11_coverage.py      # 覆盖率
```

---

## 1. 最小可运行用例：HTTP + 业务码

**知识点**

- pytest 自动发现 `test_*.py` / `test_*` 函数；
- 断言 HTTP 状态码和业务 `code` 是两件事；
- 项目统一响应：`{code,msg,data,traceId}`，业务失败可能仍是 HTTP 200。

**项目案例**：[`test_01_basic.py`](pytest/test_01_basic.py)

```python
def test_home_is_healthy(api):
    response = api.get(f"{BASE_URL}/api/home", timeout=10)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert len(body["data"]["feed"]) > 0
```

**运行**

```bash
../../pytest_automation/.venv/bin/python -m pytest test_01_basic.py -q
```

**常见坑**

- 只看 `status_code == 200`，漏掉 `code != 0` 的业务失败；
- 后端 Long 会序列化为字符串（如 `total="30"`），断言前要 `int()`。

**练习**：新增一条断言，校验首页 `slots` 中包含 `home_banner`。

---

## 2. Fixture：登录复用与作用域

**知识点**

- `scope="session"` 复用连接；
- `yield` 做 teardown；
- fixture 可以依赖 fixture；
- 每个写场景用唯一会员，避免共享账号。

**项目案例**：[`conftest.py`](pytest/conftest.py)、[`test_02_fixtures.py`](pytest/test_02_fixtures.py)

```python
@pytest.fixture
def customer(api, unique_phone):
    body = api.post(f"{BASE_URL}/api/auth/login", json={
        "phone": unique_phone, "code": "123456", "clientType": "web"
    }).json()
    token = body["data"]["accessToken"]
    return {"phone": unique_phone, "token": token,
            "headers": {"Authorization": f"Bearer {token}"}}
```

**运行**

```bash
../../pytest_automation/.venv/bin/python -m pytest test_02_fixtures.py -q
```

**常见坑**

- 用固定演示账号跑写操作，多个用例互相污染；
- fixture 里 `return` 而不是 `yield`，资源不释放；
- 手机号用同一个，短信 60 秒冷却导致偶发失败。

**练习**：把 `api` 改成 `scope="module"`，观察连接复用与隔离的差异。

---

## 3. 参数化：一套逻辑覆盖多组数据

**知识点**

- `@pytest.mark.parametrize` 把数据与逻辑分离；
- 一个参数化用例在报告里会展开成多条；
- 适合搜索命中/未命中、边界值、状态码矩阵。

**项目案例**：[`test_03_parametrize.py`](pytest/test_03_parametrize.py)

```python
@pytest.mark.parametrize("keyword,expect_hit", [
    ("iPhone", True),
    ("不存在的商品xyz", False),
])
def test_search(api, keyword, expect_hit):
    body = api.get(f"{BASE_URL}/api/search",
                   params={"q": keyword, "page": 1, "size": 10}).json()
    total = int(body["data"]["total"])
    assert (total > 0) is expect_hit
```

**运行**

```bash
../../pytest_automation/.venv/bin/python -m pytest test_03_parametrize.py -q
```

**常见坑**

- 参数化数据里放随机值，失败无法复现；
- 用例名默认只显示参数值，最好加 `ids=[...]` 提升可读性。

**练习**：把手机号 10/11/12 位做成参数化，断言 400/200/400。

---

## 4. 契约断言：字段、类型、金额

**知识点**

- 契约测试不是“字段存在”，而是类型、范围、必填、枚举；
- 金额用 `Decimal`，不要用浮点直接比较；
- SKU 列表要断言每个元素的 `skuId`、`price`、`availableStock`。

**项目案例**：[`test_04_contract.py`](pytest/test_04_contract.py)

```python
data = api.get(f"{BASE_URL}/api/products/101").json()["data"]
assert isinstance(data["spu"]["id"], str)
assert isinstance(data["skus"], list) and data["skus"]
for sku in data["skus"]:
    assert Decimal(str(sku["price"])) > 0
    assert sku["availableStock"] >= 0
```

**常见坑**

- 只断言 `code==0`，字段改名/类型变化发现不了；
- 金额用 `==` 比较浮点，出现 `199.00000001` 误判。

**练习**：为 `/api/home` 的 `feed` 增加“必须包含 `spuId/name/price`”的契约断言。

---

## 5. Marker：分层执行与 CI 门禁

**知识点**

- `@pytest.mark.smoke`、`negative`、`security`、`e2e`；
- `pytest -m smoke` 只跑冒烟；
- marker 要在 `pytest.ini` 注册，避免 `--strict-markers` 报错。

**项目案例**：[`test_05_markers.py`](pytest/test_05_markers.py)

```python
@pytest.mark.smoke
def test_categories_public(api): ...

@pytest.mark.negative
def test_cart_requires_token(api):
    assert api.get(f"{BASE_URL}/api/cart").status_code == 401
```

**运行**

```bash
../../pytest_automation/.venv/bin/python -m pytest -m smoke -q
../../pytest_automation/.venv/bin/python -m pytest -m "smoke or negative" -q
```

**常见坑**

- 所有用例都标 `smoke`，冒烟失去意义；
- marker 拼写错误，pytest 静默不选。

**练习**：给 `test_10_e2e.py` 标 `e2e`，并设计 PR 只跑 `smoke` 的策略。

---

## 6. xdist：并行与隔离

**知识点**

- `pytest -n 4` 启动 4 个 worker；
- 并行前提：无共享可变状态；
- 写用例要唯一数据，读用例可放心并行；
- 复杂项目用 `--dist loadgroup` + `xdist_group` 按接口分组。

**项目案例**：[`test_06_xdist.py`](pytest/test_06_xdist.py)

```python
@pytest.mark.parametrize("spu_id", ["101", "102", "103", "104", "121", "162"])
def test_product_detail_read_only(api, spu_id):
    body = api.get(f"{BASE_URL}/api/products/{spu_id}").json()
    assert body["code"] == 0
```

**运行**

```bash
../../pytest_automation/.venv/bin/python -m pytest test_06_xdist.py -n 4 -q
```

**常见坑**

- 多个 worker 抢同一账号/库存，出现随机失败；
- 并行后 Allure 结果目录冲突，需要每个 worker 独立目录或统一合并。

**练习**：把 `test_08_data_factory.py` 改成参数化 4 个 SKU，用 `-n 2` 跑，观察数据隔离。

---

## 7. Allure：让失败可诊断

**知识点**

- `@allure.epic/feature/story/severity` 组织报告；
- `with allure.step(...)` 记录业务步骤；
- `allure.attach` 附加请求/响应/截图；
- CI 上传 `allure-results` 并生成 HTML。

**项目案例**：[`test_07_allure.py`](pytest/test_07_allure.py)

```python
@allure.feature("商品")
@allure.story("首页运营位")
def test_home_with_allure(api):
    with allure.step("请求首页"):
        response = api.get(f"{BASE_URL}/api/home")
        allure.attach(response.text, "response.json", allure.attachment_type.JSON)
    with allure.step("断言"):
        assert response.json()["code"] == 0
```

**运行**

```bash
../../pytest_automation/.venv/bin/python -m pytest test_07_allure.py -q \
  --alluredir=../../artifacts/courseware-allure
allure serve ../../artifacts/courseware-allure
```

**常见坑**

- 只附截图不附请求/响应，API 问题无法定位；
- 附件里带 token/密码，报告外发泄露。

**练习**：给失败用例加 `allure.attach` 页面 HTML/控制台日志。

---

## 8. 数据工厂与精确清理

**知识点**

- 每个写场景生成唯一手机号；
- 资源创建后登记 ID，`finally`/fixture teardown 精确删除；
- 清理失败要让用例失败，不能静默。

**项目案例**：[`test_08_data_factory.py`](pytest/test_08_data_factory.py)

```python
created = api.post(f"{BASE_URL}/api/cart/items", headers=customer["headers"],
                   json={"skuId": "10001", "quantity": 1}).json()
cart_item_id = created["data"]["cartItemId"]
try:
    ...
finally:
    api.delete(f"{BASE_URL}/api/cart/items/{cart_item_id}",
               headers=customer["headers"])
```

**常见坑**

- 按商品标题删购物车，误删用户数据；
- 只删购物车不取消订单，库存被长期占用。

**练习**：为地址创建/删除写一个 fixture，保证用例失败也能清理。

---

## 9. Mock：不要让测试依赖外部支付

**知识点**

- 单元测试用 `unittest.mock.Mock` 替换外部客户端；
- 断言调用参数、次数、异常分支；
- 集成测试用 WireMock/responses 模拟 HTTP 依赖。

**项目案例**：[`test_09_mock.py`](pytest/test_09_mock.py)

```python
client = Mock()
client.charge.return_value = {"status": "SUCCESS"}
gateway = PaymentGateway(client)
assert gateway.pay("1", 199)["status"] == "SUCCESS"
client.charge.assert_called_once_with("1", 199)
```

**常见坑**

- Mock 了被测服务本身；
- Mock 响应与真实契约漂移，测试全绿线上失败。

**练习**：增加一个 `side_effect=TimeoutError` 的分支，断言异常处理。

---

## 10. 端到端：一条完整购买旅程

**知识点**

- E2E 只保留最有价值的 1–2 条；
- 登录 → 地址 → 下单 → 支付 → 查状态；
- 用 API 复核最终状态，不只看页面。

**项目案例**：[`test_10_e2e.py`](pytest/test_10_e2e.py)

```python
order = api.post(f"{BASE_URL}/api/orders", headers=headers, json={
    "addressId": address_id, "skuId": "10026", "quantity": 1,
    "idempotentKey": f"courseware-{uuid.uuid4()}",
}).json()
paid = api.post(f"{BASE_URL}/api/payment/sandbox", headers=headers,
                json={"orderId": order["data"]["orderId"]}).json()
assert paid["data"]["status"] == "PENDING_SHIP"
```

**运行**

```bash
../../pytest_automation/.venv/bin/python -m pytest test_10_e2e.py -q
```

**常见坑**

- E2E 用例太多，慢且 flaky；
- 支付后不校验订单状态，页面成功但后端没落库。

**练习**：在支付后查询 `/api/orders/{id}`，断言 `PENDING_SHIP`。

---

## 11. 覆盖率：先有可测函数，再有断言

**知识点**

- 行覆盖率/分支覆盖率；
- `pytest --cov` 生成报告；
- 不要为了 100% 写无断言测试；
- 核心模块单独阈值，diff 覆盖率用于 PR。

**项目案例**：[`test_11_coverage.py`](pytest/test_11_coverage.py)

```python
def freight_for(goods_amount, threshold=Decimal("99"), fee=Decimal("8")):
    return Decimal("0") if Decimal(str(goods_amount)) >= threshold else fee

def test_freight_at_threshold():
    assert freight_for("99.00") == Decimal("0")
```

**运行**

```bash
../../pytest_automation/.venv/bin/python -m pytest test_11_coverage.py \
  --cov=. --cov-report=term-missing
```

**常见坑**

- 只统计行覆盖率，不看分支；
- 把 DTO/getter 算进去，指标虚高；
- 覆盖率下降不阻断。

**练习**：给 `freight_for` 加一个负数分支，补测试并观察分支覆盖率。

---

## 12. 接入 CI：夜间回归 + 飞书

**项目案例**：[`nightly-pytest.yml`](../.github/workflows/nightly-pytest.yml)、[`scripts/ci/nightly.sh`](../pytest_automation/scripts/ci/nightly.sh)

流程：

```text
checkout → setup Python → 起 PG/Redis/MinIO → 起后端/前端
→ pytest（xdist/分层）→ Allure → 质量门禁 → artifact → 飞书
```

关键点：

- `pytest-xdist` 并行，但库存/限流用例走 serial lane；
- 失败上传 Allure、截图、日志；
- `FEISHU_WEBHOOK` 放 GitHub Secrets；
- 通知失败不拖垮测试 job（`continue-on-error`）。

**运行本地等价命令**

```bash
cd pytest_automation
bash scripts/ci/nightly.sh
```

**练习**：给 `nightly-pytest.yml` 加一个 `workflow_dispatch` 输入 `skip_ui`，并在通知里体现。

---

## 13. 课程总结

| 能力 | 对应案例 |
|---|---|
| 写最小可信用例 | test_01 |
| 复用登录/会话 | test_02 |
| 数据驱动 | test_03 |
| 契约断言 | test_04 |
| 分层执行 | test_05 |
| 并行 | test_06 |
| 报告 | test_07 |
| 数据治理 | test_08 |
| Mock | test_09 |
| E2E | test_10 |
| 覆盖率 | test_11 |
| CI/通知 | nightly-pytest.yml |

**最终练习**：把 `courseware/pytest` 接进 `nightly-pytest.yml` 的一个独立 job，要求 PR 只跑 `smoke`，夜间跑全量，并把结果发飞书。
