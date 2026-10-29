import pytest
from intervals import merge_intervals

def test_merge():
    assert merge_intervals([[8, 10], [1, 3], [2, 6], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]

def test_touching():
    assert merge_intervals([[1, 3], [3, 5]]) == [[1, 5]]

def test_contained_and_empty():
    assert merge_intervals([[1, 10], [2, 3]]) == [[1, 10]]
    assert merge_intervals([]) == []

def test_input_unchanged():
    data = [[3, 4], [1, 2]]
    merge_intervals(data)
    assert data == [[3, 4], [1, 2]]

def test_invalid():
    with pytest.raises(ValueError):
        merge_intervals([[5, 1]])
