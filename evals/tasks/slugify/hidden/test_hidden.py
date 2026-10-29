from text_utils import slugify

def test_basic():
    assert slugify("Hello World") == "hello-world"

def test_collapses_and_strips():
    assert slugify("  --Rock & Roll!!  ") == "rock-roll"

def test_digits_kept():
    assert slugify("Top 10 Tips") == "top-10-tips"

def test_non_ascii_removed():
    assert slugify("Café déjà vu") == "caf-d-j-vu"

def test_empty():
    assert slugify("!!!") == ""
    assert slugify("") == ""
