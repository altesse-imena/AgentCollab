from decimal import Decimal
from billing import order_total

def test_exact_decimal():
    assert order_total([("0.10", 1), ("0.20", 1)], "0") == Decimal("0.30")

def test_half_up():
    assert order_total([("2.675", 1)], "0") == Decimal("2.68")

def test_tax():
    assert order_total([("19.99", 3)], "0.05") == Decimal("62.97")

def test_returns_decimal():
    assert isinstance(order_total([(5, 2)], Decimal("0.1")), Decimal)
    assert order_total([(5, 2)], Decimal("0.1")) == Decimal("11.00")
