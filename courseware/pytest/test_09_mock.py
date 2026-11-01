"""知识点 9：mock 外部依赖，不真的调用支付网关。"""
from unittest.mock import Mock


class PaymentGateway:
    def __init__(self, client):
        self.client = client

    def pay(self, order_id, amount):
        return self.client.charge(order_id, amount)


def test_payment_success_with_mock():
    client = Mock()
    client.charge.return_value = {"status": "SUCCESS", "tradeNo": "SANDBOX-1"}
    gateway = PaymentGateway(client)
    result = gateway.pay("1", 199)
    assert result["status"] == "SUCCESS"
    client.charge.assert_called_once_with("1", 199)


def test_payment_failure_with_mock():
    client = Mock()
    client.charge.side_effect = TimeoutError("gateway timeout")
    gateway = PaymentGateway(client)
    try:
        gateway.pay("1", 199)
        assert False, "should raise"
    except TimeoutError as exc:
        assert "timeout" in str(exc)
