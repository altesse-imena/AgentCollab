from sessions import remove_expired

def test_removes_in_place():
    s = {"a": {"expires_at": 5}, "b": {"expires_at": 10}, "c": {"expires_at": 20}}
    assert remove_expired(s, 10) == 2
    assert list(s) == ["c"]

def test_nothing_expired():
    s = {"a": {"expires_at": 50}}
    assert remove_expired(s, 10) == 0 and "a" in s
