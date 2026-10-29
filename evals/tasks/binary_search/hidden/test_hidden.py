import pytest
from search import binary_search

ITEMS = [1, 3, 5, 7, 9, 11]

@pytest.mark.parametrize("target,index", [(1, 0), (5, 2), (11, 5), (9, 4)])
def test_found(target, index):
    assert binary_search(ITEMS, target) == index

@pytest.mark.parametrize("target", [0, 4, 12])
def test_missing(target):
    assert binary_search(ITEMS, target) == -1

def test_edges():
    assert binary_search([], 1) == -1
    assert binary_search([2], 2) == 0
