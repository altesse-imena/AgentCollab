NUMERALS = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
            (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def to_roman(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an int")
    if not 1 <= n <= 3999:
        raise ValueError("n must be between 1 and 3999")
    out = []
    for value, symbol in NUMERALS:
        count, n = divmod(n, value)
        out.append(symbol * count)
    return "".join(out)
