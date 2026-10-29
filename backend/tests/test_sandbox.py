import shutil
import subprocess
from pathlib import Path

import pytest

from agentcollab.sandbox import DockerSandbox, TestResult, build_workspace
from agentcollab.sandbox.docker import DEFAULT_IMAGE


def test_command_is_locked_down(tmp_path):
    cmd = DockerSandbox().command(tmp_path, "c1")
    joined = " ".join(cmd)
    for flag in ("--network none", "--read-only", "--cap-drop ALL", "--user 65534:65534"):
        assert flag in joined
    assert "-e" not in cmd  # no environment (and so no secrets) passed in


def test_output_is_truncated_from_the_front():
    result = TestResult.from_run(1, "x" * 20_000 + "1 failed", 5, False)
    assert not result.passed and result.output.endswith("1 failed") and len(result.output) < 9_000


def test_workspace_copies_repo_and_applies_changes(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "config").write_text("secret")
    (repo / "app.py").write_text("x = 1\n")
    ws = build_workspace(repo, tmp_path / "ws", {"app.py": "x = 2\n", "tests/test_a.py": "t"})
    assert (ws / "app.py").read_text() == "x = 2\n" and (ws / "tests/test_a.py").exists()
    assert not (ws / ".git").exists()


def _docker_ready() -> bool:
    if not shutil.which("docker"):
        return False
    probe = subprocess.run(["docker", "image", "inspect", DEFAULT_IMAGE], capture_output=True)
    return probe.returncode == 0


docker = pytest.mark.skipif(not _docker_ready(), reason="docker or sandbox image not available")


def _workspace(tmp_path: Path, test_body: str) -> Path:
    ws = tmp_path / "ws"
    (ws / "tests").mkdir(parents=True)
    (ws / "app.py").write_text("def add(a, b):\n    return a + b\n")
    (ws / "tests" / "test_app.py").write_text(f"from app import add\n\n{test_body}\n")
    (ws / "conftest.py").write_text("")  # puts the workspace root on sys.path
    return ws


@docker
def test_passing_suite(tmp_path):
    result = DockerSandbox().run_tests(
        _workspace(tmp_path, "def test_add():\n    assert add(1, 2) == 3")
    )
    assert result.passed, result.output


@docker
def test_failing_suite(tmp_path):
    result = DockerSandbox().run_tests(
        _workspace(tmp_path, "def test_add():\n    assert add(1, 2) == 4")
    )
    assert not result.passed and "1 failed" in result.output


@docker
def test_network_is_blocked(tmp_path):
    body = (
        "import socket, pytest\n\n"
        "def test_net():\n"
        "    with pytest.raises(OSError):\n"
        "        socket.create_connection(('1.1.1.1', 53), timeout=3)"
    )
    assert DockerSandbox().run_tests(_workspace(tmp_path, body)).passed


@docker
def test_timeout_kills_container(tmp_path):
    body = "import time\n\ndef test_slow():\n    time.sleep(30)"
    result = DockerSandbox(timeout_s=5).run_tests(_workspace(tmp_path, body))
    assert result.timed_out and not result.passed
