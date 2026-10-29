import argparse
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .checkpoints import open_checkpointer
from .config import get_settings
from .db import Run
from .deps import MissingAPIKey, build
from .repo import apply_files
from .service import RunOutcome, UnknownRun, resume_task, run_task


def print_outcome(outcome: RunOutcome) -> None:
    print(outcome.patch or "(no changes)")
    print(
        f"\nrun {outcome.run_id}: {outcome.status} after {outcome.iterations} round(s), "
        f"cost ${outcome.spent_usd:.4f}"
    )
    if outcome.summary:
        print(f"summary: {outcome.summary}")
    if outcome.error:
        print(f"error: {outcome.error}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(prog="agentcollab")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="turn a task into a tested, reviewed code change")
    run.add_argument("task")
    run.add_argument("--repo", type=Path, default=Path.cwd())
    run.add_argument("--budget", type=float, default=settings.agentcollab_run_budget_usd)
    run.add_argument("--max-iterations", type=int, default=3)
    run.add_argument("--apply", action="store_true", help="write the changes to disk")

    resume = sub.add_parser("resume", help="continue a run from its last saved step")
    resume.add_argument("run_id")
    resume.add_argument("--apply", action="store_true")

    sub.add_parser("runs", help="list recent runs")
    args = parser.parse_args(argv)

    try:
        engine, deps = build(settings)
    except MissingAPIKey as e:
        print(e, file=sys.stderr)
        return 2

    if args.command == "runs":
        with Session(engine) as s:
            for r in s.scalars(select(Run).order_by(Run.created_at.desc()).limit(20)):
                print(f"{r.id}  {r.status:8}  ${r.spent_usd:.4f}  {r.task[:60]}")
        return 0

    with open_checkpointer(settings.database_url) as checkpointer:
        try:
            if args.command == "run":
                outcome = run_task(
                    deps=deps,
                    engine=engine,
                    task=args.task,
                    repo=args.repo,
                    budget_usd=args.budget,
                    max_iterations=args.max_iterations,
                    checkpointer=checkpointer,
                    on_start=lambda run_id: print(f"run {run_id} started", file=sys.stderr),
                )
            else:
                outcome = resume_task(
                    deps=deps, engine=engine, run_id=args.run_id, checkpointer=checkpointer
                )
        except UnknownRun as e:
            print(f"no saved progress for run {e}", file=sys.stderr)
            return 1

    print_outcome(outcome)
    if outcome.status != "passed":
        return 1
    if args.apply:
        repo = Path(_repo_of(outcome, args))
        apply_files(repo, outcome.files)
        print(f"applied {len(outcome.files)} file(s) to {repo}")
    return 0


def _repo_of(outcome: RunOutcome, args) -> str:
    return str(args.repo) if args.command == "run" else outcome.repo_path


if __name__ == "__main__":
    raise SystemExit(main())
