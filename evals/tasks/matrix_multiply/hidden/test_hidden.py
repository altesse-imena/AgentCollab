import pytest
from matrix import matmul

def test_square():
    assert matmul([[1, 2], [3, 4]], [[5, 6], [7, 8]]) == [[19, 22], [43, 50]]

def test_rectangular():
    assert matmul([[1, 2, 3]], [[1], [2], [3]]) == [[14]]

@pytest.mark.parametrize("a,b", [([], [[1]]), ([[1, 2], [3]], [[1], [1]]), ([[1, 2]], [[1, 2]])])
def test_invalid(a, b):
    with pytest.raises(ValueError):
        matmul(a, b)
