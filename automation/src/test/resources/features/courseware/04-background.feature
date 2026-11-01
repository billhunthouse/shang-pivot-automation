@api @courseware
Feature: 课件 04 - Background 公共前置

  Background:
    Given 我用新会员身份登录

  Scenario: 加购 SKU 10001
    When 我向购物车加入 SKU "10001" 数量 1
    Then 购物车业务码应为 0

  Scenario: 加购 SKU 10026
    When 我向购物车加入 SKU "10026" 数量 1
    Then 购物车业务码应为 0
