@api @courseware @negative
Feature: 课件 05 - 负向与安全断言

  Scenario: 未登录访问购物车返回 401
    When 我未登录访问购物车
    Then 购物车接口 HTTP 状态应为 401

  Scenario: 搜索 SQL 注入不生效
    When 我匿名搜索关键词 "' OR '1'='1"
    Then 搜索结果总数应 "等于 0"
    And 响应不应包含 SQL 错误

  Scenario: 篡改签名令牌被拒绝
    Given 我有一个有效会员 token
    When 我使用 "篡改签名" 访问购物车
    Then 令牌接口 HTTP 状态应为 401
