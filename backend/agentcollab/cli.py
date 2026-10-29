import argparse
import sys
from pathlib import Path

from .config import get_settings
from .deps import MissingAPIKey, build
from .repo import apply_files
from .service import RunOutcome, run_task


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
    args = parser.parse_args(argv)

    try:
        engine, deps = build(settings)
    except MissingAPIKey as e:
        print(e, file=sys.stderr)
        return 2

    outcome = run_task(
        deps=deps,
        engine=engine,
        task=args.task,
        repo=args.repo,
        budget_usd=args.budget,
        max_iterations=args.max_iterations,
    )
    print_outcome(outcome)
    if outcome.status != "passed":
        return 1
    if args.apply:
        apply_files(args.repo, outcome.files)
        print(f"applied {len(outcome.files)} file(s) to {args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
