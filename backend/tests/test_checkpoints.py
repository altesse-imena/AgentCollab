import pytest

from agentcollab.checkpoints import open_checkpointer
from agentcollab.service import UnknownRun, resume_task, run_task
from tests.test_workflow import scripts


class CrashOnce:
    """Sandbox that dies on its first use, like a server restart mid-run."""

    def __init__(self, inner):
        self.inner, self.crashed = inner, False

    def run_tests(self, workspace, paths=None):
        if not self.crashed:
            self.crashed = True
            raise RuntimeError("server went down")
        return self.inner.run_tests(workspace, paths)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    (r / "app.py").write_text("x = 1\n")
    return r


def test_crashed_run_resumes_without_redoing_finished_steps(make_deps, engine, repo, tmp_path):
    deps, provider, sandbox = make_deps(scripts())
    deps.sandbox = CrashOnce(sandbox)
    started = []
    with open_checkpointer(f"sqlite:///{tmp_path / 'ckpt.db'}") as saver:
        with pytest.raises(RuntimeError, match="server went down"):
            run_task(deps=deps, engine=engine, task="t", repo=repo, budget_usd=1.0,
                     checkpointer=saver, on_start=started.append)  # fmt: skip
        from sqlalchemy.orm import Session

        from agentcollab.db import Run

        with Session(engine) as s:
            assert s.get(Run, started[0]).status == "crashed"
        calls_before = len(provider.calls)
        assert calls_before == 4  # writer + three parallel agents finished before the crash

        out = resume_task(deps=deps, engine=engine, run_id=started[0], checkpointer=saver)
    assert out.status == "passed"
    assert len(provider.calls) == calls_before
    with Session(engine) as s:
        assert s.get(Run, started[0]).status == "passed"  # no model calls were repeated


def test_resuming_a_finished_run_returns_its_result(make_deps, engine, repo, tmp_path):
    deps, provider, _ = make_deps(scripts())
    with open_checkpointer(f"sqlite:///{tmp_path / 'ckpt.db'}") as saver:
        first = run_task(deps=deps, engine=engine, task="t", repo=repo, budget_usd=1.0,
                         checkpointer=saver)  # fmt: skip
        again = resume_task(deps=deps, engine=engine, run_id=first.run_id, checkpointer=saver)
    assert again.status == "passed" and again.patch == first.patch and len(provider.calls) == 4


def test_unknown_run(make_deps, engine, tmp_path):
    deps, _, _ = make_deps(scripts())
    with open_checkpointer(f"sqlite:///{tmp_path / 'ckpt.db'}") as saver, pytest.raises(UnknownRun):
        resume_task(deps=deps, engine=engine, run_id="nope", checkpointer=saver)
