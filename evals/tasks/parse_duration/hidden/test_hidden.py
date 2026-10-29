import pytest
from durations import parse_duration

@pytest.mark.parametrize("text,seconds", [("45s", 45), ("1h30m", 5400), ("2h5s", 7205),
    ("1h2m3s", 3723), ("  10m ", 600), ("0s", 0)])
def test_valid(text, seconds):
    assert parse_duration(text) == seconds

@pytest.mark.parametrize("text", ["", "10", "5x", "1m1h", "1h1h", "h", "1.5h", "-1s", "1 h"])
def test_invalid(text):
    with pytest.raises(ValueError):
        parse_duration(text)
