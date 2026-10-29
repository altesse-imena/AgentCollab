"""Runs a task end to end. Week 1: CodeWriter only. Week 2 swaps this for the LangGraph workflow."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from .agents import write_code
from .db import Run
from .llm import BudgetExceeded, InvalidModelOutput, LLMClient, RunBudget
from .repo import gather_context, make_patch, safe_path
from .repo.files import UnsafePath


@dataclass
class RunOutcome:
    run_id: str
    status: str  # "passed" | "failed" | "aborted"
    summary: str
    files: dict[str, str]
    patch: str
    spent_usd: float
    error: str | None = None


def run_task(
    *,
    llm: LLMClient,
    engine: Engine,
    task: str,
    repo: Path,
    model: str,
    budget_usd: float,
) -> RunOutcome:
    run_id = str(uuid.uuid4())
    budget = RunBudget(run_id=run_id, limit_usd=budget_usd)
    with Session(engine) as s:
        s.add(Run(id=run_id, task=task, budget_usd=budget_usd))
        s.commit()

    context = gather_context(repo)
    outcome = RunOutcome(run_id, "failed", "", {}, "", 0.0)
    try:
        result = write_code(llm, model=model, task=task, context=context, budget=budget)
        files = {}
        for edit in result.output.files:
            safe_path(repo, edit.path)
            files[edit.path] = edit.content
        outcome.status = "passed"
        outcome.summary = result.output.summary
        outcome.files = files
        outcome.patch = make_patch(context, files)
    except BudgetExceeded as e:
        outcome.status, outcome.error = "aborted", str(e)
    except (InvalidModelOutput, UnsafePath) as e:
        outcome.error = str(e)
    outcome.spent_usd = budget.spent_usd

    with Session(engine) as s:
        run = s.get(Run, run_id)
        run.status = outcome.status
        run.spent_usd = outcome.spent_usd
        run.patch = outcome.patch or None
        run.error = outcome.error
        run.finished_at = datetime.now(UTC)
        s.commit()
    return outcome
