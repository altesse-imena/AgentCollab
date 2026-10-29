import pytest

from agentcollab.checkpoints import open_checkpointer
from agentcollab.db.session import make_recorder
from agentcollab.events import EventLog, combine, llm_call_recorder
from agentcollab.service import resume_task, run_task
from tests.test_checkpoints import CrashOnce
from tests.test_workflow import scripts


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    (r / "app.py").write_text("x = 1\n")
    return r


def with_events(deps, engine):
    events = EventLog(engine)
    deps.llm._record = combine(make_recorder(engine), llm_call_recorder(events))
    return events


def test_run_emits_ordered_events(make_deps, engine, repo):
    deps, _, _ = make_deps(scripts())
    events = with_events(deps, engine)
    out = run_task(deps=deps, engine=engine, task="t", repo=repo, budget_usd=1.0, events=events)
    log = events.since(out.run_id)
    assert [e["seq"] for e in log] == list(range(len(log)))
    types = [e["type"] for e in log]
    assert types[0] == "run_started" and types[-1] == "run_finished"
    assert types.count("llm_call") == 4
    finished = {e["data"]["node"]: e["data"] for e in log if e["type"] == "node_finished"}
    assert set(finished) == {
        "gather_context", "write", "review", "tests", "security", "run_tests", "judge", "finalize"
    }  # fmt: skip
    assert "+def greet" in finished["write"]["patch"]
    assert finished["judge"]["passed"] is True
    assert "context" not in str(finished["gather_context"]).replace("gather_context", "")
    assert log[-1]["data"]["status"] == "passed"


def test_since_returns_only_newer_events(make_deps, engine, repo):
    deps, _, _ = make_deps(scripts())
    events = with_events(deps, engine)
    out = run_task(deps=deps, engine=engine, task="t", repo=repo, budget_usd=1.0, events=events)
    assert [e["seq"] for e in events.since(out.run_id, after_seq=5)][0] == 6


def test_crash_and_resume_continue_the_same_log(make_deps, engine, repo, tmp_path):
    deps, _, sandbox = make_deps(scripts())
    deps.sandbox = CrashOnce(sandbox)
    started = []
    with open_checkpointer(f"sqlite:///{tmp_path / 'ckpt.db'}") as saver:
        with pytest.raises(RuntimeError):
            run_task(
                deps=deps,
                engine=engine,
                task="t",
                repo=repo,
                budget_usd=1.0,
                checkpointer=saver,
                events=EventLog(engine),
                on_start=started.append,
            )
        # a new EventLog, like a new process, must continue numbering
        resume_task(deps=deps, engine=engine, run_id=started[0], checkpointer=saver,
                    events=EventLog(engine))  # fmt: skip
    log = EventLog(engine).since(started[0])
    types = [e["type"] for e in log]
    assert "run_crashed" in types and "run_resumed" in types and types[-1] == "run_finished"
    assert [e["seq"] for e in log] == list(range(len(log)))
