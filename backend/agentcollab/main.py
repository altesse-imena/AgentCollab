"""HTTP + WebSocket API. Run with: uvicorn agentcollab.main:create_app --factory

POST /api/runs                start a run (a benchmark task, or a local repo when allowed)
GET  /api/runs                recent runs
GET  /api/runs/{id}           one run
GET  /api/tasks               benchmark tasks that can be run from the UI
WS   /api/runs/{id}/events    the run's events, live; ?speed=N replays a finished run
POST /api/github/webhook      GitHub App webhook: a labeled issue becomes a run and a draft PR
"""

import asyncio
import shutil
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .checkpoints import open_checkpointer
from .config import Settings, get_settings
from .db import Run
from .deps import MissingAPIKey, build_deps, build_store
from .evals import load_tasks
from .github import Git, GitHubApp, IssueJob, handle_issue, job_from_event, verify_signature
from .graph import Deps
from .limits import LimitReached, check_and_record, client_key
from .service import new_run_id, run_task
from .transfer import import_file

TERMINAL_EVENTS = {"run_finished", "run_crashed"}
MAX_REPLAY_GAP_S = 1.5


class StartRun(BaseModel):
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
    on_issue: Callable[[IssueJob], None] | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    engine, events = build_store(settings)
    if settings.agentcollab_seed_file and Path(settings.agentcollab_seed_file).is_file():
        import_file(engine, Path(settings.agentcollab_seed_file))
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

    def run_for_issue(task: str, workdir: Path):
        with open_checkpointer(settings.database_url) as checkpointer:
            return run_task(
                deps=get_deps(),
                engine=engine,
                task=task,
                repo=workdir,
                budget_usd=settings.agentcollab_run_budget_usd,
                checkpointer=checkpointer,
                events=events,
            )

    def handle_github_issue(job: IssueJob) -> None:
        github = GitHubApp(settings.github_app_id, settings.github_private_key_pem)
        handle_issue(
            job,
            app=github,
            git_factory=Git,
            run=run_for_issue,
            public_url=settings.agentcollab_public_url,
        )

    issue_handler = on_issue or handle_github_issue

    @app.post("/api/github/webhook", status_code=202)
    async def github_webhook(request: Request) -> dict:
        if not settings.github_enabled:
            raise HTTPException(404, "GitHub integration is not configured")
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256")
        if not verify_signature(settings.github_webhook_secret, body, signature):
            raise HTTPException(401, "bad signature")
        event = request.headers.get("X-GitHub-Event", "")
        job = job_from_event(event, await request.json(), settings.agentcollab_github_label)
        if not job:
            return {"accepted": False}
        pool.submit(issue_handler, job)
        return {"accepted": True, "repo": job.repo, "issue": job.issue}

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/tasks")
    def list_tasks() -> list[dict]:
        return [{"id": t.id, "kind": t.kind, "prompt": t.prompt} for t in tasks.values()]

    @app.get("/api/config")
    def public_config() -> dict:
        return {
            "live_runs": settings.agentcollab_live_runs,
            "runs_per_day": settings.agentcollab_runs_per_ip_per_day or None,
            "run_budget_usd": settings.agentcollab_run_budget_usd,
        }

    def client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if settings.agentcollab_trust_proxy and forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    @app.post("/api/runs", status_code=202)
    def create_run(req: StartRun, request: Request) -> dict:
        if not settings.agentcollab_live_runs:
            raise HTTPException(403, "This demo shows recorded runs only.")
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
        try:
            salt = settings.github_webhook_secret or settings.database_url
            check_and_record(engine, settings, client_key(client_ip(request), salt), run_id)
        except LimitReached as e:
            if cleanup:
                shutil.rmtree(repo.parent, ignore_errors=True)
            raise HTTPException(429, str(e)) from e
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

    # The built frontend, when present. Mounted last so /api routes take priority.
    if settings.agentcollab_static_dir and Path(settings.agentcollab_static_dir).is_dir():
        app.mount("/", StaticFiles(directory=settings.agentcollab_static_dir, html=True), "web")

    return app
