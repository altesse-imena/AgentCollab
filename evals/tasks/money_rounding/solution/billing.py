from decimal import ROUND_HALF_UP, Decimal


def order_total(items, tax_rate):
    subtotal = sum((Decimal(str(price)) * qty for price, qty in items), Decimal("0"))
    total = subtotal * (1 + Decimal(str(tax_rate)))
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
