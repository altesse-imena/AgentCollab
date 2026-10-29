def order_total(items, tax_rate):
    subtotal = sum(float(price) * qty for price, qty in items)
    return round(subtotal * (1 + float(tax_rate)), 2)
