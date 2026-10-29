import pytest
from accounts import validate_username

@pytest.mark.parametrize("name,expected", [("Alice", "alice"), ("bob_99", "bob_99"),
    ("a-b-c", "a-b-c"), ("x" * 20, "x" * 20)])
def test_valid(name, expected):
    assert validate_username(name) == expected

@pytest.mark.parametrize("name", ["ab", "x" * 21, "9lives", "_bob", "bob-", "bob_",
    "a--b", "a_-b", "bob smith", "bób", "ADMIN", "Root", "support"])
def test_invalid(name):
    with pytest.raises(ValueError):
        validate_username(name)
