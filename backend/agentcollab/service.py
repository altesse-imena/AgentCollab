"""Runs a task through the agent workflow and records the run."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from .db import Run
from .graph import Deps, build_graph
from .repo import make_patch


@dataclass
class RunOutcome:
    run_id: str
    status: str  # "passed" | "failed" | "aborted"
    summary: str
    files: dict[str, str]  # code changes plus generated tests
    patch: str
    spent_usd: float
    iterations: int
    error: str | None = None
    history: list[dict] = field(default_factory=list)


def outcome_from_state(state: dict) -> RunOutcome:
    change = state.get("change") or {"summary": "", "files": []}
    files = {f["path"]: f["content"] for f in change["files"]}
    for f in (state.get("tests") or {}).get("files", []):
        files[f["path"]] = f["content"]
    return RunOutcome(
        run_id=state["run_id"],
        status=state["status"],
        summary=change["summary"],
        files=files,
        patch=make_patch(state.get("context", {}), files) if files else "",
        spent_usd=state.get("spent_usd", 0.0),
        iterations=state.get("iteration", 0),
        error=state.get("error"),
        history=state.get("history", []),
    )


def run_task(
    *,
    deps: Deps,
    engine: Engine,
    task: str,
    repo: Path,
    budget_usd: float,
    max_iterations: int = 3,
    checkpointer=None,
) -> RunOutcome:
    run_id = str(uuid.uuid4())
    with Session(engine) as s:
        s.add(Run(id=run_id, task=task, budget_usd=budget_usd))
        s.commit()

    graph = build_graph(deps, checkpointer=checkpointer)
    state = graph.invoke(
        {
            "run_id": run_id,
            "task": task,
            "repo_path": str(repo.resolve()),
            "max_iterations": max_iterations,
            "budget_usd": budget_usd,
        },
        config={"configurable": {"thread_id": run_id}},
    )
    outcome = outcome_from_state(state)
    _save(engine, outcome)
    return outcome


def _save(engine: Engine, outcome: RunOutcome) -> None:
    with Session(engine) as s:
        run = s.get(Run, outcome.run_id)
        run.status = outcome.status
        run.spent_usd = outcome.spent_usd
        run.patch = outcome.patch or None
        run.error = outcome.error
        run.finished_at = datetime.now(UTC)
        s.commit()
