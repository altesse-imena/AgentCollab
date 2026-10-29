import subprocess
import pytest
import netcheck

class Recorder:
    def __init__(self, code=0):
        self.code, self.calls = code, []
    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, self.code)

@pytest.mark.parametrize("host", ["example.com", "8.8.8.8", "::1", "my-host.local"])
def test_valid_hosts_use_arg_list(monkeypatch, host):
    rec = Recorder()
    monkeypatch.setattr(netcheck.subprocess, "run", rec)
    assert netcheck.ping(host) is True
    args, kwargs = rec.calls[0]
    assert args == ["ping", "-c", "1", host] and not kwargs.get("shell")

def test_failure_exit_code(monkeypatch):
    monkeypatch.setattr(netcheck.subprocess, "run", Recorder(code=1))
    assert netcheck.ping("example.com") is False

@pytest.mark.parametrize("host", ["8.8.8.8; rm -rf /", "$(whoami)", "a b", "", "-c 100 x", "a" * 254])
def test_rejects_bad_hosts(monkeypatch, host):
    rec = Recorder()
    monkeypatch.setattr(netcheck.subprocess, "run", rec)
    with pytest.raises(ValueError):
        netcheck.ping(host)
    assert rec.calls == []
