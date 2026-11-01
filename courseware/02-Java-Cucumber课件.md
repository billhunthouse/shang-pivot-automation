# Java Cucumber + Allure 课件（尚品汇电商项目）

> 目标：用 BDD 把业务语言变成可执行用例，并接入 Maven、Allure、CI。
> 课件直接复用项目 `automation` 模块，不另建重复框架。
> 运行目录：`automation/`

## 0. 环境与运行

```bash
# 1. 启动被测项目
cd /Users/imac/Desktop/电商自动化测试/shang-pivot-master
bash automation/scripts/start-local.sh

# 2. 只跑课件用例
cd automation
mvn test -Dcucumber.filter.tags="@courseware"
# 预期：11 个课件场景通过，其余 74 个跳过
```

课件文件：

```text
automation/src/test/resources/features/courseware/
├── 01-home.feature
├── 02-login-outline.feature
├── 03-cart-datatable.feature
├── 04-background.feature
├── 05-negative-security.feature
└── 06-e2e.feature

automation/src/test/java/com/shangpivot/automation/steps/CoursewareSteps.java
```

`junit-platform.properties` 默认排除课件：

```properties
cucumber.filter.tags=not @known-defect and not @courseware
```

所以 `mvn test` 不会把课件混进主回归；显式传 `-Dcucumber.filter.tags="@courseware"` 才执行。

---

## 1. BDD 与 Gherkin：业务语言写用例

**知识点**

- Feature：一个业务能力；
- Scenario：一条可执行规格；
- Given/When/Then：前置、动作、断言；
- 关键字用英文，正文用中文，业务人员可读。

**项目案例**：[`01-home.feature`](../automation/src/test/resources/features/courseware/01-home.feature)

```gherkin
@api @courseware @smoke
Feature: 课件 01 - 最小可运行 BDD 用例

  Scenario: 首页健康检查
    When 我匿名请求首页
    Then 首页应返回非空商品流和运营位
    And 首页响应应符合契约
```

**运行**

```bash
mvn test -Dcucumber.filter.tags="@courseware and @smoke"
```

**常见坑**

- Step 里写 URL/选择器，业务不可读；
- 一个 Scenario 塞十几步，失败无法定位。

**练习**：新增一个 Scenario，断言首页 `slots` 至少包含一个运营位。

---

## 2. Step Definition 与 Cucumber 表达式

**知识点**

- `@When("我匿名请求首页")` 绑定 Gherkin；
- `{string}`、`{int}`、`{double}` 自动转换；
- Step 类通过 PicoContainer 注入 `ScenarioContext`；
- 一个 Step 只做一件事。

**项目案例**

- [`ApiCatalogSteps.java`](../automation/src/test/java/com/shangpivot/automation/steps/ApiCatalogSteps.java)
- [`ScenarioContext.java`](../automation/src/test/java/com/shangpivot/automation/context/ScenarioContext.java)

```java
public class ApiCatalogSteps {
    private final ScenarioContext ctx;
    public ApiCatalogSteps(ScenarioContext ctx) { this.ctx = ctx; }

    @When("我匿名请求首页")
    public void requestHome() {
        ctx.lastResult(ctx.catalog().home(20).assertSuccess());
    }
}
```

**常见坑**

- 多个 Step 文本重复，Cucumber 报 `DuplicateStepDefinition`；
- 在 Step 里 new 一堆客户端，无法复用登录态。

**练习**：给 `我匿名搜索关键词 {string}` 加一个“搜索结果应包含关键字”的 Step。

---

## 3. Scenario Outline：数据驱动

**知识点**

- `Scenario Outline` + `Examples` 把一组数据展开成多条；
- 适合登录成功/失败、边界值、状态码矩阵；
- 数据放 Feature，逻辑留 Step。

**项目案例**：[`02-login-outline.feature`](../automation/src/test/resources/features/courseware/02-login-outline.feature)

```gherkin
Scenario Outline: 手机号与验证码登录
  When 我用手机号 "<phone>" 和验证码 "<code>" 登录
  Then 登录接口 HTTP 状态应为 <http>
  And 登录业务码应为 <expected>

  Examples:
    | phone        | code   | http | expected |
    | 13900000000  | 123456 | 200  | 0        |
    | 1390000000   | 123456 | 400  | 40000    |
    | 13900000000  | 000000 | 200  | 40101    |
```

**运行**

```bash
mvn test -Dcucumber.filter.tags="@courseware and @smoke"
```

**常见坑**

- 在 Step 里 `if (phone.equals(...))`，新增数据要改代码；
- Examples 里用中文全角空格，参数匹配失败。

**练习**：增加一行“验证码 5 位”，断言 `40101`。

---

## 4. DataTable：批量数据

**知识点**

- `DataTable` 适合“一组商品/一组字段”；
- `table.asMaps()` 转 `List<Map<String,String>>`；
- 批量造数后要登记清理。

**项目案例**：[`03-cart-datatable.feature`](../automation/src/test/resources/features/courseware/03-cart-datatable.feature)、[`CoursewareSteps.java`](../automation/src/test/java/com/shangpivot/automation/steps/CoursewareSteps.java)

```gherkin
When 我批量加入以下商品：
  | skuId | quantity |
  | 10001 | 1        |
  | 10026 | 2        |
Then 购物车应包含以下商品：
  | skuId | quantity |
  | 10001 | 1        |
```

```java
@When("我批量加入以下商品：")
public void bulkAdd(DataTable table) {
    for (Map<String, String> row : table.asMaps()) {
        ctx.cart().add(row.get("skuId"), Integer.parseInt(row.get("quantity")));
    }
}
```

**常见坑**

- DataTable 第一行被当成数据，忘记表头；
- 批量写数据不登记，结束后不清理。

**练习**：把 DataTable 改成 3 个 SKU，并增加“总金额 = 单价×数量”断言。

---

## 5. Background：公共前置

**知识点**

- `Background` 在每个 Scenario 前执行；
- 适合“已登录”这种所有场景都需要的前置；
- 不要把某个场景专属步骤放 Background。

**项目案例**：[`04-background.feature`](../automation/src/test/resources/features/courseware/04-background.feature)

```gherkin
Background:
  Given 我用新会员身份登录

Scenario: 加购 SKU 10001
  When 我向购物车加入 SKU "10001" 数量 1
  Then 购物车业务码应为 0
```

**常见坑**

- Background 里做写操作，每个场景重复造数；
- Background 失败时所有场景都失败，难以定位。

**练习**：把“准备默认收货地址”也放进 Background，观察执行次数。

---

## 6. Tags 与 Hooks：分层与生命周期

**知识点**

- `@api/@ui/@smoke/@regression/@negative/@security/@courseware`；
- `@Before/@After` 做场景生命周期；
- `@After` 里做清理，失败留证；
- 标签可组合：`@courseware and not @negative`。

**项目案例**

- [`Hooks.java`](../automation/src/test/java/com/shangpivot/automation/hooks/Hooks.java)
- [`05-negative-security.feature`](../automation/src/test/resources/features/courseware/05-negative-security.feature)

```java
@Before(order = 0)
public void before(Scenario scenario) {
    EnvironmentProbe.verifyOnce();
    if (scenario.getSourceTagNames().contains("@ui")) {
        browser.start(scenario.getName());
    }
}
```

**运行**

```bash
mvn test -Dcucumber.filter.tags="@courseware and @negative"
```

**常见坑**

- 在 Step 里手动清理，失败时跳过；
- 所有场景都起浏览器，API 用例被拖慢。

**练习**：给课件加一个 `@courseware @security` 场景，统计 Allure 标签。

---

## 7. API Client 与断言：分层

**知识点**

- Feature → Step → API Client → RestClient；
- Step 不拼 URL/JSON；
- 断言统一封装：HTTP 状态、业务 code、Schema、DB；
- `ScenarioContext` 在场景内共享 token/订单号。

**项目案例**

- [`ApiCartAddressSteps.java`](../automation/src/test/java/com/shangpivot/automation/steps/ApiCartAddressSteps.java)
- [`CartApi.java`](../automation/src/test/java/com/shangpivot/automation/api/CartApi.java)
- [`ApiResult.java`](../automation/src/test/java/com/shangpivot/automation/core/api/ApiResult.java)

```java
ApiResult result = ctx.cart().add("10001", 2).assertSuccess();
String cartItemId = result.data().path("cartItemId").asText();
```

**常见坑**

- Step 里直接 `given().when().get()`，无法复用/统一日志；
- 只断言 HTTP 200，漏业务失败。

**练习**：给购物车加购封装一个“断言金额 = 单价×数量”的领域方法。

---

## 8. Allure：步骤、附件、环境

**知识点**

- Cucumber 插件自动把 Feature/Scenario 映射到 Allure；
- 每个 API 请求/响应自动附件；
- UI 失败附截图/DOM/控制台/trace；
- 报告有环境、标签、耗时。

**项目案例**

- [`AllureSupport.java`](../automation/src/test/java/com/shangpivot/automation/core/allure/AllureSupport.java)
- [`Hooks.java`](../automation/src/test/java/com/shangpivot/automation/hooks/Hooks.java)

**运行**

```bash
mvn test -Dcucumber.filter.tags="@courseware"
allure generate target/allure-results -o artifacts/allure-report --clean
python3 -m http.server 18080 --directory artifacts/allure-report
```

**常见坑**

- 只生成 cucumber-report，不生成 Allure；
- 附件带 token/密码未脱敏。

**练习**：在课件 Step 里加一个 `Allure.addAttachment("购物车", ...)`。

---

## 9. 负向与安全：不该发生的事

**知识点**

- 未登录 401、越权 403/404、SQL 注入不生效、篡改 token 401；
- 断言“状态码 + 业务码 + 数据未变”；
- 安全用例只允许测试环境、合成数据。

**项目案例**：[`05-negative-security.feature`](../automation/src/test/resources/features/courseware/05-negative-security.feature)

```gherkin
Scenario: 搜索 SQL 注入不生效
  When 我匿名搜索关键词 "' OR '1'='1"
  Then 搜索结果总数应 "等于 0"
  And 响应不应包含 SQL 错误
```

**运行**

```bash
mvn test -Dcucumber.filter.tags="@courseware and @negative"
```

**常见坑**

- 只断言“请求失败”，没断言业务码/数据未变；
- 在生产环境跑注入/爆破。

**练习**：增加“用户 A 访问用户 B 订单”的 Step，断言 404 且不泄露手机号。

---

## 10. 端到端：API 购买旅程

**知识点**

- 登录 → 地址 → 下单 → 支付 → 状态；
- 用 API 复核最终状态；
- E2E 只保留少量核心链路。

**项目案例**：[`06-e2e.feature`](../automation/src/test/resources/features/courseware/06-e2e.feature)

```gherkin
Scenario: 登录 → 地址 → 下单 → 支付
  Given 我用新会员身份登录
  And 我通过接口准备默认收货地址
  When 我准备一个含 SKU "10026" 数量 1 的待支付订单
  And 我对该订单发起沙箱支付
  Then 订单状态应变为 PENDING_SHIP 且交易号以 SANDBOX- 开头
```

**常见坑**

- 只跑 UI 不校验后端状态；
- 支付后不清理/不隔离会员，后续用例受污染。

**练习**：在支付后增加“订单详情状态 = PENDING_SHIP”的断言。

---

## 11. 并行、标签与 CI

**知识点**

- Cucumber 并行：`cucumber.execution.parallel.enabled=true`；
- 并行前提：场景数据隔离；
- CI 中只跑 `@courseware` 或 `@smoke`；
- Allure 结果上传 artifact。

**运行**

```bash
mvn test -Dcucumber.filter.tags="@courseware" \
  -Dcucumber.execution.parallel.enabled=true \
  -Dcucumber.execution.parallel.config.strategy=fixed \
  -Dcucumber.execution.parallel.config.fixed.parallelism=2
```

**CI 对应**

- [`.github/workflows/e2e.yml`](../.github/workflows/e2e.yml)
- 手动 `tags` 输入，默认 `not @known-defect`
- Allure artifact + 飞书通知

**常见坑**

- 并行时共享会员/购物车，出现随机失败；
- 安全/故障注入用例并行互相干扰。

**练习**：把课件拆成 `@courseware @api` 和 `@courseware @e2e` 两组，分别跑。

---

## 12. 课程总结

| 能力 | 对应文件 |
|---|---|
| Feature/Scenario | 01-home.feature |
| Step/表达式 | ApiCatalogSteps.java |
| Scenario Outline | 02-login-outline.feature |
| DataTable | 03-cart-datatable.feature + CoursewareSteps |
| Background | 04-background.feature |
| Tags/Hooks | Hooks.java |
| API 分层 | CartApi/ApiResult |
| Allure | AllureSupport/Hooks |
| 负向安全 | 05-negative-security.feature |
| E2E | 06-e2e.feature |
| 并行/CI | e2e.yml |

**最终练习**：新增一个 `@courseware @ui` 场景，从商城首页加购并断言购物车；要求失败时 Allure 有截图和 trace。
