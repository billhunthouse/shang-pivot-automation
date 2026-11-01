"""知识点 11：覆盖率——先有可测函数，再有断言。"""
from decimal import Decimal


def freight_for(goods_amount, threshold=Decimal("99"), fee=Decimal("8")):
    amount = Decimal(str(goods_amount))
    return Decimal("0") if amount >= threshold else fee


def test_freight_below_threshold():
    assert freight_for("98.99") == Decimal("8")


def test_freight_at_threshold():
    assert freight_for("99.00") == Decimal("0")


def test_freight_above_threshold():
    assert freight_for("99.01") == Decimal("0")
