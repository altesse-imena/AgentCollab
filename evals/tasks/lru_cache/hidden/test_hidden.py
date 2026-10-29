import pytest
from lru import LRUCache

def test_get_put():
    c = LRUCache(2)
    c.put("a", 1)
    assert c.get("a") == 1 and c.get("missing") is None

def test_evicts_least_recent():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2)
    c.get("a")
    c.put("c", 3)
    assert c.get("b") is None and c.get("a") == 1 and c.get("c") == 3
    assert len(c) == 2

def test_update_refreshes():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2); c.put("a", 10); c.put("c", 3)
    assert c.get("a") == 10 and c.get("b") is None

def test_invalid_capacity():
    with pytest.raises(ValueError):
        LRUCache(0)
