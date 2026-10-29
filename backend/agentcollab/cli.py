import argparse
import sys
from pathlib import Path

from .config import get_settings
from .db import make_engine, make_recorder
from .llm import LLMClient
from .llm.providers import OpenAIProvider
from .repo import apply_files
from .service import run_task


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(prog="agentcollab")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="turn a task into a code change")
    run.add_argument("task")
    run.add_argument("--repo", type=Path, default=Path.cwd())
    run.add_argument("--model", default=settings.agentcollab_writer_model)
    run.add_argument("--budget", type=float, default=settings.agentcollab_run_budget_usd)
    run.add_argument("--apply", action="store_true", help="write the changes to disk")
    args = parser.parse_args(argv)

    if not settings.openai_api_key:
        print("OPENAI_API_KEY is not set (add it to backend/.env)", file=sys.stderr)
        return 2

    engine = make_engine(settings.database_url)
    llm = LLMClient(OpenAIProvider(settings.openai_api_key), recorder=make_recorder(engine))
    outcome = run_task(
        llm=llm, engine=engine, task=args.task, repo=args.repo, model=args.model,
        budget_usd=args.budget,
    )

    print(outcome.patch or "(no changes)")
    print(f"\nrun {outcome.run_id}: {outcome.status}, cost ${outcome.spent_usd:.4f}")
    if outcome.summary:
        print(f"summary: {outcome.summary}")
    if outcome.error:
        print(f"error: {outcome.error}", file=sys.stderr)
        return 1
    if args.apply:
        apply_files(args.repo, outcome.files)
        print(f"applied {len(outcome.files)} file(s) to {args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
