"""Benchmark: run the workflow on evals/tasks and grade each result with hidden tests.

Each task folder has:
  task.json            {"id", "kind", "prompt"}
  repo/                starting code the agents see
  hidden/test_*.py     tests the agents never see, used only for grading
  solution/            reference fix, used by --check to validate the task itself
"""

import json
import shutil
import statistics
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from .db import LLMCall
from .graph import Deps
from .sandbox import Sandbox, TestResult, build_workspace
from .service import run_task

EVALS_DIR = Path(__file__).resolve().parents[2] / "evals"
HIDDEN_DIR = "_hidden_tests"  # where hidden tests go in the grading workspace


@dataclass
class EvalTask:
    id: str
    kind: str
    prompt: str
    path: Path


@dataclass
class TaskResult:
    id: str
    kind: str
    status: str  # what the workflow reported
    hidden_passed: bool  # what actually counts
    cost_usd: float
    iterations: int
    duration_s: float
    llm_calls: int
    prompt_tokens: int
    cached_tokens: int
    error: str | None = None


def load_tasks(tasks_dir: Path = EVALS_DIR / "tasks", only: list[str] | None = None):
    tasks = []
    for meta in sorted(tasks_dir.glob("*/task.json")):
        data = json.loads(meta.read_text())
        if only and data["id"] not in only:
            continue
        tasks.append(EvalTask(data["id"], data["kind"], data["prompt"], meta.parent))
    return tasks


def grade(sandbox: Sandbox, task: EvalTask, changes: dict[str, str]) -> TestResult:
    """Run the hidden tests against the starting repo plus the given changes."""
    files = dict(changes)
    for test in (task.path / "hidden").glob("*.py"):
        files[f"{HIDDEN_DIR}/{test.name}"] = test.read_text()
    with tempfile.TemporaryDirectory(prefix="agentcollab-eval-") as tmp:
        ws = build_workspace(task.path / "repo", Path(tmp) / "ws", files)
        return sandbox.run_tests(ws, paths=[HIDDEN_DIR])


def check_task(sandbox: Sandbox, task: EvalTask) -> list[str]:
    """A valid task fails its hidden tests as given and passes them with the solution."""
    problems = []
    if grade(sandbox, task, {}).passed:
        problems.append("hidden tests already pass on the starting code")
    solution = {
        p.relative_to(task.path / "solution").as_posix(): p.read_text()
        for p in (task.path / "solution").rglob("*")
        if p.is_file()
    }
    result = grade(sandbox, task, solution)
    if not result.passed:
        problems.append(f"reference solution fails hidden tests:\n{result.output[-1500:]}")
    return problems


def _usage(engine: Engine, run_id: str) -> tuple[int, int, int]:
    with Session(engine) as s:
        row = s.execute(
            select(
                func.count(LLMCall.id),
                func.coalesce(func.sum(LLMCall.prompt_tokens), 0),
                func.coalesce(func.sum(LLMCall.cached_tokens), 0),
            ).where(LLMCall.run_id == run_id)
        ).one()
    return int(row[0]), int(row[1]), int(row[2])


def run_eval(
    tasks: list[EvalTask],
    *,
    deps: Deps,
    engine: Engine,
    budget_usd: float,
    max_iterations: int,
    log=print,
) -> list[TaskResult]:
    results = []
    for task in tasks:
        with tempfile.TemporaryDirectory(prefix="agentcollab-task-") as tmp:
            repo = Path(tmp) / "repo"  # a copy, so the hidden tests are never in reach
            shutil.copytree(task.path / "repo", repo)
            start = time.perf_counter()
            outcome = run_task(
                deps=deps,
                engine=engine,
                task=task.prompt,
                repo=repo,
                budget_usd=budget_usd,
                max_iterations=max_iterations,
            )
            duration = time.perf_counter() - start
        hidden = grade(deps.sandbox, task, outcome.files) if outcome.files else None
        calls, prompt_tokens, cached = _usage(engine, outcome.run_id)
        result = TaskResult(
            id=task.id,
            kind=task.kind,
            status=outcome.status,
            hidden_passed=bool(hidden and hidden.passed),
            cost_usd=round(outcome.spent_usd, 6),
            iterations=outcome.iterations,
            duration_s=round(duration, 1),
            llm_calls=calls,
            prompt_tokens=prompt_tokens,
            cached_tokens=cached,
            error=outcome.error,
        )
        log(
            f"{task.id:22} {'PASS' if result.hidden_passed else 'FAIL'}  "
            f"${result.cost_usd:.4f}  {result.iterations} round(s)  {result.duration_s}s"
        )
        results.append(result)
    return results


def summarize(results: list[TaskResult]) -> dict:
    n = len(results) or 1
    prompt = sum(r.prompt_tokens for r in results)
    return {
        "tasks": len(results),
        "pass_rate": round(sum(r.hidden_passed for r in results) / n, 3),
        "total_cost_usd": round(sum(r.cost_usd for r in results), 4),
        "avg_cost_usd": round(sum(r.cost_usd for r in results) / n, 4),
        "median_duration_s": statistics.median([r.duration_s for r in results]) if results else 0,
        "avg_iterations": round(sum(r.iterations for r in results) / n, 2),
        "cache_hit_rate": round(sum(r.cached_tokens for r in results) / prompt, 3) if prompt else 0,
    }


def save_results(label: str, results: list[TaskResult], config: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize(results)
    data = {
        "label": label,
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config": config,
        "summary": summary,
        "results": [asdict(r) for r in results],
    }
    path = out_dir / f"{label}.json"
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path


def compare(paths: list[Path]) -> str:
    """A markdown table comparing saved results; changes are relative to the first one."""
    runs = [json.loads(p.read_text()) for p in paths]
    base = runs[0]["summary"]

    def change(value: float, base_value: float) -> str:
        if not base_value or value == base_value:
            return ""
        return f" ({(value - base_value) / base_value:+.0%})"

    rows = [
        "| Config | Pass rate | Avg cost / task | Median time | Avg rounds | Prompt cache |",
        "|---|---|---|---|---|---|",
    ]
    for r in runs:
        s = r["summary"]
        passed = round(s["pass_rate"] * s["tasks"])
        cost = f"${s['avg_cost_usd']:.4f}{change(s['avg_cost_usd'], base['avg_cost_usd'])}"
        rows.append(
            f"| {r['label']} | {s['pass_rate']:.0%} ({passed}/{s['tasks']}) | {cost} "
            f"| {s['median_duration_s']}s | {s['avg_iterations']} | {s['cache_hit_rate']:.0%} |"
        )
    return "\n".join(rows)
