"""Export runs (with their events and model calls) to JSON and import them elsewhere.

Used to ship real recorded runs with a deployment, so a replay-only demo needs no database
migration and no API key.
"""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from .db import LLMCall, Run, RunEvent

RUN_FIELDS = ("id", "task", "status", "budget_usd", "spent_usd", "patch", "error")
CALL_FIELDS = (
    "agent", "model", "prompt_tokens", "cached_tokens", "completion_tokens", "cost_usd",
    "latency_ms", "attempt", "cache_hit",
)  # fmt: skip


def _ts(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def export_runs(engine: Engine, run_ids: list[str]) -> dict:
    out = []
    with Session(engine) as s:
        for run_id in run_ids:
            run = s.get(Run, run_id)
            if not run:
                raise LookupError(f"no run {run_id}")
            events = s.scalars(
                select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.seq)
            ).all()
            calls = s.scalars(
                select(LLMCall).where(LLMCall.run_id == run_id).order_by(LLMCall.id)
            ).all()
            out.append(
                {
                    **{f: getattr(run, f) for f in RUN_FIELDS},
                    "created_at": _ts(run.created_at),
                    "finished_at": _ts(run.finished_at),
                    "events": [
                        {"seq": e.seq, "type": e.type, "data": e.data, "at": _ts(e.created_at)}
                        for e in events
                    ],
                    "llm_calls": [
                        {**{f: getattr(c, f) for f in CALL_FIELDS}, "at": _ts(c.created_at)}
                        for c in calls
                    ],
                }
            )
    return {"version": 1, "runs": out}


def import_runs(engine: Engine, data: dict) -> int:
    """Adds runs that aren't already present. Returns how many were added."""
    added = 0
    with Session(engine) as s:
        for r in data["runs"]:
            if s.get(Run, r["id"]):
                continue
            s.add(
                Run(
                    **{f: r[f] for f in RUN_FIELDS},
                    created_at=datetime.fromisoformat(r["created_at"]),
                    finished_at=datetime.fromisoformat(r["finished_at"])
                    if r["finished_at"]
                    else None,
                )
            )
            s.flush()
            for e in r["events"]:
                s.add(
                    RunEvent(
                        run_id=r["id"], seq=e["seq"], type=e["type"], data=e["data"],
                        created_at=datetime.fromisoformat(e["at"]),
                    )
                )  # fmt: skip
            for c in r["llm_calls"]:
                fields = {f: c[f] for f in CALL_FIELDS}
                s.add(LLMCall(run_id=r["id"], created_at=datetime.fromisoformat(c["at"]), **fields))
            added += 1
        s.commit()
    return added


def import_file(engine: Engine, path: Path) -> int:
    return import_runs(engine, json.loads(path.read_text()))
