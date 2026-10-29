"""HTTP + WebSocket API. Run with: uvicorn agentcollab.main:create_app --factory

POST /api/runs                start a run (a benchmark task, or a local repo when allowed)
GET  /api/runs                recent runs
GET  /api/runs/{id}           one run
GET  /api/tasks               benchmark tasks that can be run from the UI
WS   /api/runs/{id}/events    the run's events, live; ?speed=N replays a finished run
"""

import asyncio
import shutil
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .checkpoints import open_checkpointer
from .config import Settings, get_settings
from .db import Run
from .deps import MissingAPIKey, build_deps, build_store
from .evals import load_tasks
from .graph import Deps
from .service import new_run_id, run_task

TERMINAL_EVENTS = {"run_finished", "run_crashed"}
MAX_REPLAY_GAP_S = 1.5


class RunRequest(BaseModel):
    task_id: str | None = None  # a benchmark task
    task: str | None = None  # free text, with repo_path
    repo_path: str | None = None
    max_iterations: int = 3

    @model_validator(mode="after")
    def one_source(self):
        if bool(self.task_id) == bool(self.task and self.repo_path):
            raise ValueError("give either task_id, or task and repo_path")
        if not 1 <= self.max_iterations <= 5:
            raise ValueError("max_iterations must be 1 to 5")
        return self


def run_summary(r: Run) -> dict:
    return {
        "id": r.id,
        "task": r.task,
        "status": r.status,
        "spent_usd": r.spent_usd,
        "budget_usd": r.budget_usd,
        "created_at": r.created_at.isoformat(),
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "error": r.error,
    }


def create_app(
    settings: Settings | None = None,
    deps_factory: Callable[..., Deps] = build_deps,
) -> FastAPI:
    settings = settings or get_settings()
    engine, events = build_store(settings)
    pool = ThreadPoolExecutor(max_workers=settings.agentcollab_max_concurrent_runs)
    tasks = {t.id: t for t in load_tasks()}
    app = FastAPI(title="AgentCollab")
    app.state.pool = pool

    def get_deps() -> Deps:
        if getattr(app.state, "deps", None) is None:
            app.state.deps = deps_factory(settings, engine, events)
        return app.state.deps

    def execute(run_id: str, task: str, repo: Path, max_iterations: int, cleanup: bool) -> None:
        try:
            with open_checkpointer(settings.database_url) as checkpointer:
                run_task(
                    deps=get_deps(),
                    engine=engine,
                    task=task,
                    repo=repo,
                    budget_usd=settings.agentcollab_run_budget_usd,
                    max_iterations=max_iterations,
                    checkpointer=checkpointer,
                    events=events,
                    run_id=run_id,
                )
        except Exception:
            pass  # recorded as a run_crashed event; the run can be resumed
        finally:
            if cleanup:
                shutil.rmtree(repo.parent, ignore_errors=True)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/tasks")
    def list_tasks() -> list[dict]:
        return [{"id": t.id, "kind": t.kind, "prompt": t.prompt} for t in tasks.values()]

    @app.post("/api/runs", status_code=202)
    def create_run(req: RunRequest) -> dict:
        try:
            get_deps()
        except MissingAPIKey as e:
            raise HTTPException(503, str(e)) from e
        if req.task_id:
            if req.task_id not in tasks:
                raise HTTPException(404, f"unknown task {req.task_id}")
            t = tasks[req.task_id]
            repo = Path(tempfile.mkdtemp(prefix="agentcollab-api-")) / "repo"
            shutil.copytree(t.path / "repo", repo)  # never includes the hidden tests
            prompt, cleanup = t.prompt, True
        else:
            if not settings.agentcollab_allow_local_repos:
                raise HTTPException(403, "local repos are disabled on this server")
            repo = Path(req.repo_path)
            if not repo.is_dir():
                raise HTTPException(400, "repo_path is not a directory")
            prompt, cleanup = req.task, False
        run_id = new_run_id()
        pool.submit(execute, run_id, prompt, repo, req.max_iterations, cleanup)
        return {"run_id": run_id}

    @app.get("/api/runs")
    def list_runs(limit: int = 20) -> list[dict]:
        with Session(engine) as s:
            rows = s.scalars(select(Run).order_by(Run.created_at.desc()).limit(min(limit, 100)))
            return [run_summary(r) for r in rows]

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        with Session(engine) as s:
            run = s.get(Run, run_id)
            if not run:
                raise HTTPException(404, "run not found")
            return run_summary(run)

    @app.websocket("/api/runs/{run_id}/events")
    async def stream_events(ws: WebSocket, run_id: str, after: int = -1, speed: float = 0):
        """Sends events as they happen. With speed > 0, paces a finished run's events by
        their original timing (sped up by `speed`) so it plays back like a live run."""
        await ws.accept()
        last_at: datetime | None = None
        try:
            while True:
                batch = await asyncio.to_thread(events.since, run_id, after)
                for event in batch:
                    if speed > 0:
                        at = datetime.fromisoformat(event["at"])
                        if last_at:
                            gap = (at - last_at).total_seconds() / speed
                            await asyncio.sleep(min(max(gap, 0), MAX_REPLAY_GAP_S))
                        last_at = at
                    await ws.send_json(event)
                    after = event["seq"]
                    if event["type"] in TERMINAL_EVENTS:
                        await ws.close()
                        return
                if not batch:
                    await asyncio.sleep(0.3)
        except WebSocketDisconnect:
            return

    return app
