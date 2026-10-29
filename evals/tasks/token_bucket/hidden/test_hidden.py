import pytest
from ratelimit import TokenBucket

class Clock:
    def __init__(self):
        self.t = 0.0
    def __call__(self):
        return self.t

def test_starts_full_and_drains():
    b = TokenBucket(3, 1, clock=Clock())
    assert [b.allow() for _ in range(4)] == [True, True, True, False]

def test_refills_over_time_capped():
    clock = Clock()
    b = TokenBucket(2, 1, clock=clock)
    b.allow(); b.allow()
    clock.t = 1.5
    assert b.allow() and not b.allow()
    clock.t = 100
    assert b.allow(2) and not b.allow()

def test_failed_allow_does_not_spend():
    b = TokenBucket(2, 1, clock=Clock())
    assert not b.allow(3)
    assert b.allow(2)

@pytest.mark.parametrize("cap,rate", [(0, 1), (1, 0), (-1, 1)])
def test_invalid(cap, rate):
    with pytest.raises(ValueError):
        TokenBucket(cap, rate)
