import shutil
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from ..repo.context import SKIP_DIRS
from ..repo.files import apply_files

MAX_OUTPUT_CHARS = 8_000


class TestResult(BaseModel):
    __test__ = False  # not a pytest class

    passed: bool
    exit_code: int | None
    output: str
    duration_ms: int
    timed_out: bool = False

    @classmethod
    def from_run(cls, exit_code: int | None, output: str, duration_ms: int, timed_out: bool):
        if len(output) > MAX_OUTPUT_CHARS:  # keep the end: that's where pytest's summary is
            output = "...(truncated)...\n" + output[-MAX_OUTPUT_CHARS:]
        return cls(
            passed=exit_code == 0 and not timed_out,
            exit_code=exit_code,
            output=output,
            duration_ms=duration_ms,
            timed_out=timed_out,
        )


class Sandbox(Protocol):
    """Runs the test suite of a prepared workspace somewhere isolated from this machine."""

    def run_tests(self, workspace: Path, paths: list[str] | None = None) -> TestResult:
        """Run pytest in the workspace, optionally limited to some test paths."""
        ...


def build_workspace(repo: Path, dest: Path, changes: dict[str, str]) -> Path:
    """Copy the repo (minus .git, venvs and build output) and apply the proposed changes."""
    shutil.copytree(repo, dest, ignore=shutil.ignore_patterns(*SKIP_DIRS), dirs_exist_ok=True)
    apply_files(dest, changes)
    return dest
