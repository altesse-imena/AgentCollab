from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import get_settings
from .deps import MissingAPIKey, build
from .service import run_task

app = FastAPI(title="AgentCollab")


class RunRequest(BaseModel):
    task: str
    repo_path: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/runs")
def create_run(req: RunRequest) -> dict:
    # Local-only for now: runs against a path on this machine. Week 5 adds async runs + live updates.
    settings = get_settings()
    try:
        engine, llm = build(settings)
    except MissingAPIKey as e:
        raise HTTPException(503, str(e)) from e
    repo = Path(req.repo_path)
    if not repo.is_dir():
        raise HTTPException(400, "repo_path is not a directory")
    outcome = run_task(
        llm=llm, engine=engine, task=req.task, repo=repo,
        model=settings.model_for("writer"), budget_usd=settings.agentcollab_run_budget_usd,
    )
    return outcome.__dict__
