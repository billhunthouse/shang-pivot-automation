@api @courseware @e2e
Feature: 课件 06 - API 端到端购买旅程

  Scenario: 登录 → 地址 → 下单 → 支付
    Given 我用新会员身份登录
    And 我通过接口准备默认收货地址
    When 我准备一个含 SKU "10026" 数量 1 的待支付订单
    And 我对该订单发起沙箱支付
    Then 订单状态应变为 PENDING_SHIP 且交易号以 SANDBOX- 开头
