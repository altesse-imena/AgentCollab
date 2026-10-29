from sqlalchemy.orm import Session

from agentcollab.db import Run
from agentcollab.service import run_task


def run(llm, engine, repo, budget=1.0):
    return run_task(llm=llm, engine=engine, task="add a greet function", repo=repo,
                    model="gpt-4.1", budget_usd=budget)


def test_successful_run_produces_patch_and_saves_run(make_llm, engine, tmp_path):
    (tmp_path / "app.py").write_text("x = 1\n")
    llm, provider = make_llm([{"summary": "added greet", "files": [
        {"path": "app.py", "content": "x = 1\n\ndef greet():\n    return 'hi'\n"}]}])
    out = run(llm, engine, tmp_path)
    assert out.status == "passed"
    assert "+def greet():" in out.patch
    assert "x = 1" in provider.calls[0]["messages"][1]["content"]  # repo context was sent
    assert (tmp_path / "app.py").read_text() == "x = 1\n"  # nothing written without --apply
    with Session(engine) as s:
        saved = s.get(Run, out.run_id)
        assert saved.status == "passed" and saved.spent_usd > 0 and saved.finished_at


def test_unsafe_path_from_model_fails_run(make_llm, engine, tmp_path):
    llm, _ = make_llm([{"summary": "evil", "files": [{"path": "../outside.py", "content": "x"}]}])
    out = run(llm, engine, tmp_path)
    assert out.status == "failed" and "refusing path" in out.error


def test_zero_budget_aborts(make_llm, engine, tmp_path):
    llm, provider = make_llm([])
    out = run(llm, engine, tmp_path, budget=0.0)
    assert out.status == "aborted" and provider.calls == []
