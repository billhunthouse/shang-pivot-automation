@api @courseware @smoke
Feature: 课件 02 - Scenario Outline 数据驱动

  Scenario Outline: 手机号与验证码登录
    When 我用手机号 "<phone>" 和验证码 "<code>" 登录
    Then 登录接口 HTTP 状态应为 <http>
    And 登录业务码应为 <expected>

    Examples:
      | phone        | code   | http | expected |
      | 13900000000  | 123456 | 200  | 0        |
      | 1390000000   | 123456 | 400  | 40000    |
      | 13900000000  | 000000 | 200  | 40101    |
