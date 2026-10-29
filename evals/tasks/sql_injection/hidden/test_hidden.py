import sqlite3
import pytest
from users import find_user

@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    c.executemany("INSERT INTO users (name) VALUES (?)", [("alice",), ("bob",), ("o'brien",)])
    return c

def test_finds_user(conn):
    assert find_user(conn, "bob") == (2, "bob")

def test_quotes_in_names(conn):
    assert find_user(conn, "o'brien") == (3, "o'brien")

def test_injection_returns_nothing(conn):
    assert find_user(conn, "' OR '1'='1") is None
