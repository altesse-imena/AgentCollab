from words import top_words

def test_counts_case_insensitive():
    assert top_words("The cat and the hat. THE end", 1) == [("the", 3)]

def test_ties_alphabetical():
    assert top_words("b a c b a c", 3) == [("a", 2), ("b", 2), ("c", 2)]

def test_apostrophes_and_punctuation():
    assert top_words("Don't stop, don't!", 2) == [("don't", 2), ("stop", 1)]

def test_n_bounds():
    assert top_words("one two", 0) == []
    assert top_words("one two", 10) == [("one", 1), ("two", 1)]
