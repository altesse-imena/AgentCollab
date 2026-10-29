import pytest
from pagination import paginate

ITEMS = list(range(1, 11))

def test_first_page():
    assert paginate(ITEMS, 1, 3) == [1, 2, 3]

def test_last_partial_page():
    assert paginate(ITEMS, 4, 3) == [10]

def test_past_end():
    assert paginate(ITEMS, 5, 3) == []

@pytest.mark.parametrize("page,size", [(0, 3), (1, 0), (-1, 2)])
def test_invalid(page, size):
    with pytest.raises(ValueError):
        paginate(ITEMS, page, size)
