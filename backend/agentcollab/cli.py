import argparse
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .checkpoints import open_checkpointer
from .config import ROLES, get_settings
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

    ev = sub.add_parser("eval", help="run the benchmark in evals/tasks")
    ev.add_argument("--label", default="latest", help="results go to evals/results/<label>.json")
    ev.add_argument("--tasks", help="comma-separated task ids (default: all)")
    ev.add_argument("--budget", type=float, default=settings.agentcollab_run_budget_usd)
    ev.add_argument("--max-iterations", type=int, default=3)
    ev.add_argument("--check", action="store_true", help="validate the tasks; no model calls")
    args = parser.parse_args(argv)

    if args.command == "eval" and args.check:
        return _check_tasks(args)

    try:
        engine, deps, events = build(settings)
    except MissingAPIKey as e:
        print(e, file=sys.stderr)
        return 2

    if args.command == "eval":
        return _run_eval(args, settings, engine, deps)

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
                    events=events,
                )
            else:
                outcome = resume_task(
                    deps=deps,
                    engine=engine,
                    run_id=args.run_id,
                    checkpointer=checkpointer,
                    events=events,
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


def _check_tasks(args) -> int:
    from .evals import check_task, load_tasks
    from .sandbox import DockerSandbox

    sandbox = DockerSandbox(timeout_s=20)
    failures = 0
    for task in load_tasks(only=args.tasks.split(",") if args.tasks else None):
        problems = check_task(sandbox, task)
        failures += bool(problems)
        print(f"{task.id:22} {'ok' if not problems else 'INVALID'}")
        for p in problems:
            print(f"    {p}")
    return 1 if failures else 0


def _run_eval(args, settings, engine, deps) -> int:
    from .evals import EVALS_DIR, load_tasks, run_eval, save_results

    tasks = load_tasks(only=args.tasks.split(",") if args.tasks else None)
    results = run_eval(
        tasks,
        deps=deps,
        engine=engine,
        budget_usd=args.budget,
        max_iterations=args.max_iterations,
    )
    config = {
        "provider": settings.agentcollab_provider,
        "models": {role: settings.model_for(role) for role in ROLES},
        "max_iterations": args.max_iterations,
        "budget_usd": args.budget,
    }
    path = save_results(args.label, results, config, EVALS_DIR / "results")
    print(f"\nsaved {path}")
    return 0


def _repo_of(outcome: RunOutcome, args) -> str:
    return str(args.repo) if args.command == "run" else outcome.repo_path


if __name__ == "__main__":
    raise SystemExit(main())
