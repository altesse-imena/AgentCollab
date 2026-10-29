from fastapi.testclient import TestClient

from agentcollab.config import Settings
from agentcollab.db import make_engine
from agentcollab.events import EventLog
from agentcollab.main import create_app
from agentcollab.service import run_task
from agentcollab.transfer import export_runs, import_runs
from tests.test_api import collect, fake_factory
from tests.test_events import with_events
from tests.test_workflow import scripts


def recorded_run(make_deps, engine, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n")
    deps, _, _ = make_deps(scripts())
    events = with_events(deps, engine)
    return run_task(deps=deps, engine=engine, task="t", repo=repo, budget_usd=1.0, events=events)


def test_export_import_round_trip(make_deps, engine, tmp_path):
    out = recorded_run(make_deps, engine, tmp_path)
    data = export_runs(engine, [out.run_id])
    other = make_engine(f"sqlite:///{tmp_path / 'other.db'}")
    assert import_runs(other, data) == 1
    assert import_runs(other, data) == 0  # idempotent
    assert EventLog(other).since(out.run_id) == EventLog(engine).since(out.run_id)
    assert export_runs(other, [out.run_id]) == data


def test_server_seeds_runs_and_serves_frontend(make_deps, engine, tmp_path):
    import json

    out = recorded_run(make_deps, engine, tmp_path)
    seed = tmp_path / "runs.json"
    seed.write_text(json.dumps(export_runs(engine, [out.run_id])))
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<h1>AgentCollab</h1>")
    s = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'server.db'}",
        agentcollab_seed_file=str(seed),
        agentcollab_static_dir=str(static),
        agentcollab_live_runs=False,
    )
    client = TestClient(create_app(s, deps_factory=fake_factory))
    assert client.get("/").text == "<h1>AgentCollab</h1>"
    assert client.get("/api/health").json() == {"status": "ok"}
    assert collect(client, out.run_id, speed=1000)[-1]["data"]["status"] == "passed"
