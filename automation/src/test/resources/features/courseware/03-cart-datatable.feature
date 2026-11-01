@api @courseware
Feature: 课件 03 - DataTable 批量数据

  Scenario: 批量加购并校验数量
    Given 我用新会员身份登录
    When 我批量加入以下商品：
      | skuId | quantity |
      | 10001 | 1        |
      | 10026 | 2        |
    Then 购物车应包含以下商品：
      | skuId | quantity |
      | 10001 | 1        |
      | 10026 | 2        |
