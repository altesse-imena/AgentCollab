"""Run events: node starts and finishes, model calls, and the final outcome.

Events are stored in the database, so any process can stream them (the API polls by
sequence number) and finished runs can be replayed later.
"""

import threading
from collections import defaultdict
from datetime import datetime

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from .db import RunEvent

NODE_LABELS = {
    "gather_context": "ContextGatherer",
    "write": "CodeWriter",
    "review": "CodeReviewer",
    "tests": "TestGenerator",
    "security": "SecurityAnalyzer",
    "run_tests": "TestRunner",
    "judge": "Judge",
    "finalize": "Finalize",
}


class EventLog:
    def __init__(self, engine: Engine):
        self.engine = engine
        self._lock = threading.Lock()
        self._next: dict[str, int] = defaultdict(int)

    def emit(self, run_id: str, type: str, data: dict) -> None:
        with self._lock, Session(self.engine) as s:
            if run_id not in self._next:  # continuing a run (e.g. resume) in a new process
                last = s.scalar(select(func.max(RunEvent.seq)).where(RunEvent.run_id == run_id))
                self._next[run_id] = (last or 0) + 1 if last is not None else 0
            seq = self._next[run_id]
            self._next[run_id] += 1
            s.add(RunEvent(run_id=run_id, seq=seq, type=type, data=data))
            s.commit()

    def since(self, run_id: str, after_seq: int = -1, limit: int = 500) -> list[dict]:
        with Session(self.engine) as s:
            rows = s.scalars(
                select(RunEvent)
                .where(RunEvent.run_id == run_id, RunEvent.seq > after_seq)
                .order_by(RunEvent.seq)
                .limit(limit)
            ).all()
            return [to_dict(r) for r in rows]


def to_dict(e: RunEvent) -> dict:
    ts: datetime = e.created_at
    return {"seq": e.seq, "type": e.type, "data": e.data, "at": ts.isoformat()}


def node_summary(node: str, update: dict | None) -> dict:
    """The parts of a node's result worth showing; never the full repo contents."""
    u = update or {}
    match node:
        case "gather_context":
            return {"files": sorted(u.get("context", {}))}
        case "write":
            change = u.get("change") or {}
            return {
                "iteration": u.get("iteration"),
                "summary": change.get("summary"),
                "files": [f["path"] for f in change.get("files", [])],
                "patch": u.get("patch"),
                "status": u.get("status"),
                "error": u.get("error"),
            }
        case "review" | "security" | "tests":
            return {
                "output": u.get(node),
                "error": (u.get("agent_errors") or {}).get(
                    {
                        "review": "code_reviewer",
                        "security": "security_analyzer",
                        "tests": "test_generator",
                    }[node]  # fmt: skip
                ),
            }
        case "run_tests":
            return {"result": u.get("test_result")}
        case "judge":
            history = u.get("history") or [{}]
            return {**history[-1], "status": u.get("status"), "error": u.get("error")}
        case _:
            return {}


def llm_call_recorder(events: EventLog):
    """A recorder callback that also streams each model call."""

    def record(call) -> None:
        events.emit(
            call.run_id,
            "llm_call",
            {
                "agent": call.agent,
                "model": call.model,
                "prompt_tokens": call.prompt_tokens,
                "cached_tokens": call.cached_tokens,
                "completion_tokens": call.completion_tokens,
                "cost_usd": call.cost_usd,
                "latency_ms": call.latency_ms,
                "cache_hit": call.cache_hit,
            },
        )

    return record


def combine(*recorders):
    def record(call) -> None:
        for r in recorders:
            r(call)

    return record
