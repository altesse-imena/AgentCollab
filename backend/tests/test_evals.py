import json

from agentcollab.evals import load_tasks, run_eval, save_results, summarize
from tests.test_sandbox import docker


def test_all_tasks_load_with_hidden_tests_and_solutions():
    tasks = load_tasks()
    assert len(tasks) >= 20
    for t in tasks:
        assert t.prompt and list((t.path / "hidden").glob("test_*.py"))
        assert list((t.path / "solution").iterdir()) and list((t.path / "repo").iterdir())


def test_agents_never_see_hidden_tests(make_deps, engine):
    task = load_tasks(only=["slugify"])[0]
    solution = (task.path / "solution" / "text_utils.py").read_text()
    deps, provider, sandbox = make_deps(
        {
            "writer": [{"summary": "s", "files": [{"path": "text_utils.py", "content": solution}]}],
            "reviewer": [{"approved": True, "comments": []}],
            "tester": [{"files": [{"path": "tests/test_agentcollab_s.py", "content": "x"}]}],
            "security": [{"findings": []}],
        }
    )
    results = run_eval([task], deps=deps, engine=engine, budget_usd=1.0, max_iterations=1,
                       log=lambda _: None)  # fmt: skip
    prompts = " ".join(m["content"] for c in provider.calls for m in c["messages"])
    assert "test_hidden" not in prompts and "caf-d-j-vu" not in prompts
    # workflow's sandbox run had no hidden tests; the grading run did
    assert not any(k.startswith("_hidden_tests") for k in sandbox.workspaces[0])
    assert "_hidden_tests/test_hidden.py" in sandbox.workspaces[-1]
    assert results[0].hidden_passed and results[0].llm_calls == 4


def test_summary_and_saved_file(tmp_path, make_deps, engine):
    task = load_tasks(only=["slugify"])[0]
    deps, _, _ = make_deps(
        {"writer": ["bad", "bad"], "reviewer": [{}], "tester": [{}], "security": [{}]}
    )
    results = run_eval([task], deps=deps, engine=engine, budget_usd=1.0, max_iterations=1,
                       log=lambda _: None)  # fmt: skip
    assert summarize(results)["pass_rate"] == 0
    path = save_results("unit", results, {"provider": "fake"}, tmp_path)
    assert json.loads(path.read_text())["results"][0]["status"] == "failed"


@docker
def test_check_flags_a_broken_task(tmp_path):
    from agentcollab.evals import EvalTask, check_task
    from agentcollab.sandbox import DockerSandbox

    for sub, body in (
        ("repo", "def f():\n    return 1\n"),
        ("solution", "def f():\n    return 1\n"),
    ):
        (tmp_path / sub).mkdir()
        (tmp_path / sub / "m.py").write_text(body)
    (tmp_path / "hidden").mkdir()
    (tmp_path / "hidden" / "test_hidden.py").write_text(
        "from m import f\n\ndef test_f():\n    assert f() == 2\n"
    )
    problems = check_task(DockerSandbox(timeout_s=20), EvalTask("t", "bug", "p", tmp_path))
    assert any("solution fails" in p for p in problems)


def test_compare_table(tmp_path):
    from agentcollab.evals import TaskResult, compare

    def result(cost, passed):
        return TaskResult("t", "bug", "passed", passed, cost, 1, 10.0, 4, 1000, 500)

    a = save_results("baseline", [result(0.10, True), result(0.10, False)], {}, tmp_path)
    b = save_results("light", [result(0.06, True), result(0.06, True)], {}, tmp_path)
    table = compare([a, b])
    assert "| baseline | 50% (1/2) | $0.1000 |" in table
    assert "| light | 100% (2/2) | $0.0600 (-40%) |" in table
