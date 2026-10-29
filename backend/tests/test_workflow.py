import pytest
from sqlalchemy.orm import Session

from agentcollab.db import Run
from agentcollab.service import run_task

WRITE = {
    "summary": "added greet",
    "files": [{"path": "app.py", "content": "def greet():\n    return 'hi'\n"}],
}
APPROVE = {"approved": True, "comments": []}
CLEAN = {"findings": []}
TESTS = {"files": [{"path": "tests/test_agentcollab_greet.py", "content": "def test_greet(): ..."}]}
BLOCKER = {
    "approved": False,
    "comments": [
        {"path": "app.py", "line": 1, "severity": "blocker", "message": "returns wrong text"}
    ],
}
SQLI = {
    "findings": [
        {"path": "app.py", "severity": "high", "cwe": "CWE-89", "issue": "SQL built with f-string",
         "fix": "use parameters"}
    ]
}  # fmt: skip


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    (r / "app.py").write_text("x = 1\n")
    return r


def scripts(**overrides):
    base = {"writer": [WRITE], "reviewer": [APPROVE], "tester": [TESTS], "security": [CLEAN]}
    return {**base, **overrides}


def run(deps, engine, repo, **kw):
    return run_task(deps=deps, engine=engine, task="add greet", repo=repo, budget_usd=1.0, **kw)


def test_happy_path_passes_in_one_round(make_deps, engine, repo):
    deps, provider, sandbox = make_deps(scripts())
    out = run(deps, engine, repo)
    assert out.status == "passed" and out.iterations == 1
    assert sorted(c["role"] for c in provider.calls) == ["reviewer", "security", "tester", "writer"]
    # the sandbox got the repo, the change and the generated tests
    ws = sandbox.workspaces[0]
    assert "def greet" in ws["app.py"] and "tests/test_agentcollab_greet.py" in ws
    assert "tests/test_agentcollab_greet.py" in out.files and "+def greet" in out.patch
    assert (repo / "app.py").read_text() == "x = 1\n"  # the real repo is untouched
    with Session(engine) as s:
        saved = s.get(Run, out.run_id)
        assert saved.status == "passed" and saved.spent_usd == pytest.approx(out.spent_usd)


def test_failing_tests_send_output_back_to_writer(make_deps, engine, repo):
    deps, provider, _ = make_deps(scripts(), sandbox_results=[False, True])
    out = run(deps, engine, repo)
    assert out.status == "passed" and out.iterations == 2
    second = provider.for_role("writer")[1]["messages"][1]["content"]
    assert "Test run failed" in second and "assert 1 == 2" in second
    assert [h["passed"] for h in out.history] == [False, True]


def test_blocking_review_and_security_trigger_another_round(make_deps, engine, repo):
    deps, provider, _ = make_deps(scripts(reviewer=[BLOCKER, APPROVE], security=[SQLI, CLEAN]))
    out = run(deps, engine, repo)
    assert out.status == "passed" and out.iterations == 2
    feedback = provider.for_role("writer")[1]["messages"][1]["content"]
    assert "returns wrong text" in feedback and "CWE-89" in feedback


def test_gives_up_after_max_iterations(make_deps, engine, repo):
    deps, provider, _ = make_deps(scripts(), sandbox_results=[False])
    out = run(deps, engine, repo, max_iterations=2)
    assert out.status == "failed" and out.iterations == 2 and "2 rounds" in out.error
    assert len(provider.for_role("writer")) == 2
    assert out.files  # the best attempt is still returned


def test_one_agent_failing_does_not_stop_the_round(make_deps, engine, repo):
    deps, _, _ = make_deps(scripts(reviewer=["not json", "still not json"]))
    out = run(deps, engine, repo)
    assert out.status == "passed"
    assert "code_reviewer" in out.history[0]["agent_errors"]


def test_agent_errors_reset_each_round(make_deps, engine, repo):
    deps, _, _ = make_deps(scripts(reviewer=["bad", "bad", APPROVE]), sandbox_results=[False, True])
    out = run(deps, engine, repo)
    assert "code_reviewer" in out.history[0]["agent_errors"]
    assert out.history[1]["agent_errors"] == {}


def test_writer_failure_ends_run_without_testing(make_deps, engine, repo):
    deps, provider, sandbox = make_deps(scripts(writer=["nope", "nope"]))
    out = run(deps, engine, repo)
    assert out.status == "failed" and out.error.startswith("code_writer")
    assert sandbox.workspaces == [] and {c["role"] for c in provider.calls} == {"writer"}


def test_unsafe_path_from_writer_fails_run(make_deps, engine, repo):
    evil = {"summary": "x", "files": [{"path": "../outside.py", "content": "x"}]}
    deps, _, _ = make_deps(scripts(writer=[evil]))
    out = run(deps, engine, repo)
    assert out.status == "failed" and "refusing path" in out.error


def test_budget_exhaustion_aborts(make_deps, engine, repo):
    # each fake call costs ~$0.0057; four calls per round
    deps, _, _ = make_deps(scripts(), sandbox_results=[False])
    out = run_task(deps=deps, engine=engine, task="t", repo=repo, budget_usd=0.01)
    assert out.status == "aborted"
    assert out.spent_usd < 0.01 + 4 * 0.006  # stops within one round of the limit
