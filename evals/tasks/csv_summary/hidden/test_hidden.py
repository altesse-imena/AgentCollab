from report import column_means

def test_numeric_columns():
    text = "name,age,score\nann,30,90.5\nbob,40,80\n"
    assert column_means(text) == {"age": 35.0, "score": 85.25}

def test_skips_empty_and_mixed():
    text = "a,b,c\n1,x,\n,2,\n3,4,\n"
    assert column_means(text) == {"a": 2.0}

def test_quoted_values():
    text = 'city,pop\n"Paris, FR",3\n"Rome, IT",4\n'
    assert column_means(text) == {"pop": 3.5}
