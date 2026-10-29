import pytest

from agentcollab.agents import analyze_security, generate_tests, review_code
from agentcollab.llm import InvalidModelOutput, RunBudget

ARGS = {
    "model": "gpt-4.1",
    "task": "add greet",
    "context": {"app.py": "x = 1\n"},
    "patch": "+def greet(): ...",
    "changed": {"app.py": "def greet(): ..."},
}


def budget():
    return RunBudget("r1", limit_usd=1.0)


def test_reviewer_parses_comments_and_blocking(make_llm):
    llm, provider = make_llm(
        [
            {
                "approved": False,
                "comments": [
                    {
                        "path": "app.py",
                        "line": 1,
                        "severity": "major",
                        "message": "no docstring handling",
                    },
                    {"path": "app.py", "severity": "nit", "message": "naming"},
                ],
            }
        ]
    )
    review = review_code(llm, budget=budget(), **ARGS).output
    assert not review.approved and len(review.blocking) == 1
    user = provider.calls[0]["messages"][1]["content"]
    assert "x = 1" in user and "+def greet()" in user  # sees context and the diff


def test_security_blocking_only_high_and_critical(make_llm):
    llm, _ = make_llm(
        [
            {
                "findings": [
                    {
                        "path": "a.py",
                        "severity": "high",
                        "cwe": "CWE-78",
                        "issue": "shell=True",
                        "fix": "pass a list",
                    },
                    {"path": "a.py", "severity": "low", "issue": "verbose error", "fix": "trim"},
                ]
            }
        ]
    )
    report = analyze_security(llm, budget=budget(), **ARGS).output
    assert [f.cwe for f in report.blocking] == ["CWE-78"]


def test_security_empty_findings_is_valid(make_llm):
    llm, _ = make_llm([{"findings": []}])
    assert analyze_security(llm, budget=budget(), **ARGS).output.blocking == []


def test_tester_accepts_test_files(make_llm):
    llm, _ = make_llm(
        [{"files": [{"path": "tests/test_agentcollab_greet.py", "content": "def test_x(): pass"}]}]
    )
    suite = generate_tests(llm, budget=budget(), **ARGS).output
    assert suite.files[0].path == "tests/test_agentcollab_greet.py"


def test_tester_rejects_non_test_paths_after_repair(make_llm):
    bad = {"files": [{"path": "app.py", "content": "overwrite source"}]}
    llm, provider = make_llm([bad, bad])
    with pytest.raises(InvalidModelOutput):
        generate_tests(llm, budget=budget(), **ARGS)
    assert "tests/test_" in provider.calls[1]["messages"][-1]["content"]  # repair saw the reason
