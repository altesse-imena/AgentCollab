from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import get_settings
from .db import make_engine, make_recorder
from .llm import LLMClient
from .llm.providers import OpenAIProvider
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
    if not settings.openai_api_key:
        raise HTTPException(503, "OPENAI_API_KEY is not set")
    repo = Path(req.repo_path)
    if not repo.is_dir():
        raise HTTPException(400, "repo_path is not a directory")
    engine = make_engine(settings.database_url)
    llm = LLMClient(OpenAIProvider(settings.openai_api_key), recorder=make_recorder(engine))
    outcome = run_task(
        llm=llm, engine=engine, task=req.task, repo=repo,
        model=settings.agentcollab_writer_model, budget_usd=settings.agentcollab_run_budget_usd,
    )
    return outcome.__dict__
