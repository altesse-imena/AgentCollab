import pytest
from roman import to_roman

@pytest.mark.parametrize("n,expected", [(1, "I"), (4, "IV"), (9, "IX"), (14, "XIV"), (40, "XL"),
    (90, "XC"), (400, "CD"), (900, "CM"), (1994, "MCMXCIV"), (2024, "MMXXIV"), (3999, "MMMCMXCIX")])
def test_values(n, expected):
    assert to_roman(n) == expected

@pytest.mark.parametrize("n", [0, -5, 4000])
def test_out_of_range(n):
    with pytest.raises(ValueError):
        to_roman(n)

@pytest.mark.parametrize("n", [1.5, "5", True])
def test_wrong_type(n):
    with pytest.raises(TypeError):
        to_roman(n)
