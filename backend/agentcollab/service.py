"""Runs a task through the agent workflow and records the run."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from .db import Run
from .events import NODE_LABELS, EventLog, node_summary
from .graph import Deps, build_graph
from .repo import make_patch


@dataclass
class RunOutcome:
    run_id: str
    repo_path: str
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
        repo_path=state["repo_path"],
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
    on_start: Callable[[str], None] | None = None,
    events: EventLog | None = None,
    run_id: str | None = None,
) -> RunOutcome:
    run_id = run_id or new_run_id()
    with Session(engine) as s:
        s.add(Run(id=run_id, task=task, budget_usd=budget_usd))
        s.commit()
    if events:
        events.emit(run_id, "run_started", {"task": task, "budget_usd": budget_usd,
                                            "max_iterations": max_iterations})  # fmt: skip
    if on_start:
        on_start(run_id)  # lets callers show the id, which is needed to resume after a crash

    graph = build_graph(deps, checkpointer=checkpointer)
    initial = {
        "run_id": run_id,
        "task": task,
        "repo_path": str(repo.resolve()),
        "max_iterations": max_iterations,
        "budget_usd": budget_usd,
    }
    state = _execute(graph, initial, run_id, events)
    return _finish(engine, events, state)


def _execute(graph, graph_input, run_id: str, events: EventLog | None) -> dict:
    """Run the graph, emitting an event as each node starts and finishes."""
    config = {"configurable": {"thread_id": run_id}}
    state = None
    try:
        for mode, chunk in graph.stream(graph_input, config, stream_mode=["tasks", "values"]):
            if mode == "values":
                state = chunk
            elif events and chunk["name"] in NODE_LABELS:
                node = chunk["name"]
                if "result" in chunk:  # finished
                    data = {"node": node, "label": NODE_LABELS[node],
                            **node_summary(node, chunk["result"])}  # fmt: skip
                    events.emit(run_id, "node_finished", data)
                else:
                    events.emit(run_id, "node_started", {"node": node, "label": NODE_LABELS[node]})
    except Exception as e:
        if events:
            events.emit(run_id, "run_crashed", {"error": f"{type(e).__name__}: {e}"})
        raise
    return state


def _finish(engine: Engine, events: EventLog | None, state: dict) -> RunOutcome:
    outcome = outcome_from_state(state)
    _save(engine, outcome)
    if events:
        events.emit(
            outcome.run_id,
            "run_finished",
            {
                k: getattr(outcome, k)
                for k in (
                    "status",
                    "summary",
                    "patch",
                    "spent_usd",
                    "iterations",
                    "error",
                    "history",
                )
            }  # fmt: skip
            | {"files": sorted(outcome.files)},
        )
    return outcome


def new_run_id() -> str:
    return str(uuid.uuid4())


class UnknownRun(LookupError):
    pass


def resume_task(
    *, deps: Deps, engine: Engine, run_id: str, checkpointer, events: EventLog | None = None
) -> RunOutcome:
    """Continue a run from its last saved step (e.g. after a crash)."""
    graph = build_graph(deps, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": run_id}}
    snapshot = graph.get_state(config)
    if not snapshot.values:
        raise UnknownRun(run_id)
    # Nothing left to run means it already finished; otherwise pick up from the saved step
    if not snapshot.next:
        return outcome_from_state(snapshot.values)
    if events:
        events.emit(run_id, "run_resumed", {})
    state = _execute(graph, None, run_id, events)
    return _finish(engine, events, state)


def _save(engine: Engine, outcome: RunOutcome) -> None:
    with Session(engine) as s:
        run = s.get(Run, outcome.run_id)
        run.status = outcome.status
        run.spent_usd = outcome.spent_usd
        run.patch = outcome.patch or None
        run.error = outcome.error
        run.finished_at = datetime.now(UTC)
        s.commit()
