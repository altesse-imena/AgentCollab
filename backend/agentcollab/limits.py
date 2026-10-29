"""Spending and rate limits for runs started through the public API."""

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from .config import Settings
from .db import Run, RunRequest


class LimitReached(Exception):
    pass


def client_key(ip: str, salt: str) -> str:
    """A stable per-visitor key that doesn't store the IP itself."""
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:32]


def check_and_record(engine: Engine, settings: Settings, client: str, run_id: str) -> None:
    since = datetime.now(UTC) - timedelta(days=1)
    with Session(engine) as s:
        if settings.agentcollab_runs_per_ip_per_day:
            used = s.scalar(
                select(func.count(RunRequest.id)).where(
                    RunRequest.client == client, RunRequest.created_at >= since
                )
            )
            if used >= settings.agentcollab_runs_per_ip_per_day:
                raise LimitReached(
                    f"You've used today's {settings.agentcollab_runs_per_ip_per_day} runs. "
                    "Recorded runs can still be replayed."
                )
        if settings.agentcollab_daily_budget_usd:
            # Finished runs count at their actual cost, unfinished ones at their full budget
            rows = s.execute(
                select(Run.spent_usd, Run.budget_usd, Run.finished_at).where(
                    Run.created_at >= since
                )
            ).all()
            committed = sum(r.spent_usd if r.finished_at else r.budget_usd for r in rows)
            if (
                committed + settings.agentcollab_run_budget_usd
                > settings.agentcollab_daily_budget_usd
            ):
                raise LimitReached(
                    "The demo has reached today's spending limit. Recorded runs can still be "
                    "replayed."
                )
        s.add(RunRequest(client=client, run_id=run_id))
        s.commit()
