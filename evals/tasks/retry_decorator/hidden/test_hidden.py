import pytest
from retry import retry

def make(fail_times):
    calls = []
    @retry(3)
    def flaky():
        """Docs."""
        calls.append(1)
        if len(calls) <= fail_times:
            raise RuntimeError(f"fail {len(calls)}")
        return "ok"
    return flaky, calls

def test_succeeds_after_failures():
    fn, calls = make(2)
    assert fn() == "ok" and len(calls) == 3

def test_reraises_last_error():
    fn, calls = make(5)
    with pytest.raises(RuntimeError, match="fail 3"):
        fn()
    assert len(calls) == 3

def test_metadata():
    fn, _ = make(0)
    assert fn.__name__ == "flaky" and fn.__doc__ == "Docs."
