@api @courseware @smoke
Feature: 课件 01 - 最小可运行 BDD 用例

  Scenario: 首页健康检查
    When 我匿名请求首页
    Then 首页应返回非空商品流和运营位
    And 首页响应应符合契约
