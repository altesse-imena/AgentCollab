import subprocess
import time
import uuid
from pathlib import Path

from .base import TestResult

DEFAULT_IMAGE = "agentcollab-sandbox:latest"
TEST_COMMAND = ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--color=no"]


class DockerSandbox:
    """One throwaway container per run: no network, capped CPU/memory/processes, non-root,
    read-only root filesystem, and only the workspace mounted. No secrets are passed in."""

    def __init__(
        self,
        image: str = DEFAULT_IMAGE,
        timeout_s: int = 60,
        cpus: str = "1",
        memory: str = "512m",
        docker: str = "docker",
    ):
        self.image, self.timeout_s, self.cpus, self.memory = image, timeout_s, cpus, memory
        self.docker = docker

    def command(self, workspace: Path, name: str, paths: list[str] | None = None) -> list[str]:
        return [
            self.docker, "run", "--rm", "--name", name,
            "--network", "none",
            "--cpus", self.cpus, "--memory", self.memory, "--memory-swap", self.memory,
            "--pids-limit", "256",
            "--user", "65534:65534",
            "--read-only", "--tmpfs", "/tmp:rw,size=64m",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "-v", f"{workspace.resolve()}:/work:rw", "-w", "/work",
            self.image, *TEST_COMMAND, "--", *(paths or []),
        ]  # fmt: skip

    def run_tests(self, workspace: Path, paths: list[str] | None = None) -> TestResult:
        workspace.chmod(0o777)  # the container's unprivileged user must be able to write here
        name = f"agentcollab-{uuid.uuid4().hex[:12]}"
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                self.command(workspace, name, paths),
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
            exit_code, output, timed_out = proc.returncode, proc.stdout + proc.stderr, False
        except subprocess.TimeoutExpired as e:
            subprocess.run([self.docker, "kill", name], capture_output=True)
            out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            exit_code, output, timed_out = None, out + f"\nTimed out after {self.timeout_s}s", True
        return TestResult.from_run(
            exit_code, output, int((time.perf_counter() - start) * 1000), timed_out
        )


def build_image(image: str = DEFAULT_IMAGE, docker: str = "docker") -> None:
    context = Path(__file__).resolve().parents[2] / "sandbox-image"
    subprocess.run([docker, "build", "-t", image, str(context)], check=True)
