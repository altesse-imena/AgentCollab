from flatten import flatten

def test_deep():
    assert flatten([1, [2, [3, [4, (5, 6)]]], 7]) == [1, 2, 3, 4, 5, 6, 7]

def test_strings_atomic():
    assert flatten(["ab", ["cd", [b"ef"]]]) == ["ab", "cd", b"ef"]

def test_empty():
    assert flatten([[], [[]], ()]) == []
