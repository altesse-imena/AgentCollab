import time

import pytest
from fastapi.testclient import TestClient

from agentcollab.config import Settings
from agentcollab.db.session import make_recorder
from agentcollab.deps import MissingAPIKey
from agentcollab.events import combine, llm_call_recorder
from agentcollab.graph import Deps
from agentcollab.llm import LLMClient
from agentcollab.main import create_app
from tests.conftest import FakeSandbox, RoleFakeProvider
from tests.test_workflow import scripts


def fake_factory(settings, engine, events):
    recorder = combine(make_recorder(engine), llm_call_recorder(events))
    llm = LLMClient(RoleFakeProvider(scripts()), recorder=recorder, wait_max_s=0)
    return Deps(llm=llm, sandbox=FakeSandbox([True]), model_for=lambda r: "gpt-4.1")


def no_key_factory(settings, engine, events):
    raise MissingAPIKey("OPENAI_API_KEY is not set")


@pytest.fixture
def make_client(tmp_path):
    def _make(factory=fake_factory, **settings):
        s = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'api.db'}", **settings)
        return TestClient(create_app(s, deps_factory=factory))

    return _make


def collect(client, run_id, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    with client.websocket_connect(f"/api/runs/{run_id}/events?{query}") as ws:
        events = []
        while True:
            event = ws.receive_json()
            events.append(event)
            if event["type"] in ("run_finished", "run_crashed"):
                return events


def test_health_and_tasks(make_client):
    client = make_client()
    assert client.get("/api/health").json() == {"status": "ok"}
    tasks = client.get("/api/tasks").json()
    assert len(tasks) >= 20 and {"id", "kind", "prompt"} <= tasks[0].keys()


def test_benchmark_task_runs_in_background_and_streams(make_client):
    client = make_client()
    resp = client.post("/api/runs", json={"task_id": "slugify"})
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]
    events = collect(client, run_id)
    assert events[0]["type"] == "run_started" and events[-1]["data"]["status"] == "passed"
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "passed"
    assert client.get("/api/runs").json()[0]["id"] == run_id


def test_replay_matches_live_events_and_resumes_from_seq(make_client):
    client = make_client()
    run_id = client.post("/api/runs", json={"task_id": "slugify"}).json()["run_id"]
    live = collect(client, run_id)
    start = time.perf_counter()
    replay = collect(client, run_id, speed=1000)
    assert replay == live and time.perf_counter() - start < 5
    assert collect(client, run_id, after=live[-3]["seq"]) == live[-2:]


def test_missing_key_rejects_new_runs_but_replays_still_work(make_client):
    client = make_client(factory=no_key_factory)
    resp = client.post("/api/runs", json={"task_id": "slugify"})
    assert resp.status_code == 503 and "OPENAI_API_KEY" in resp.json()["detail"]
    assert client.get("/api/tasks").status_code == 200


def test_local_repos_need_opt_in(make_client, tmp_path):
    body = {"task": "do it", "repo_path": str(tmp_path)}
    assert make_client().post("/api/runs", json=body).status_code == 403
    allowed = make_client(agentcollab_allow_local_repos=True)
    assert allowed.post("/api/runs", json=body).status_code == 202


@pytest.mark.parametrize(
    "body",
    [{}, {"task": "x"}, {"task_id": "slugify", "task": "x", "repo_path": "/"},
     {"task_id": "slugify", "max_iterations": 9}],
)  # fmt: skip
def test_bad_requests(make_client, body):
    assert make_client().post("/api/runs", json=body).status_code == 422


def test_unknown_task(make_client):
    assert make_client().post("/api/runs", json={"task_id": "nope"}).status_code == 404


def test_replay_only_mode(make_client):
    client = make_client(agentcollab_live_runs=False)
    assert client.get("/api/config").json()["live_runs"] is False
    assert client.post("/api/runs", json={"task_id": "slugify"}).status_code == 403


def test_per_visitor_daily_limit(make_client):
    client = make_client(agentcollab_runs_per_ip_per_day=1)
    assert client.post("/api/runs", json={"task_id": "slugify"}).status_code == 202
    second = client.post("/api/runs", json={"task_id": "slugify"})
    assert second.status_code == 429 and "today's 1 runs" in second.json()["detail"]


def test_proxy_header_only_trusted_when_enabled(make_client):
    client = make_client(agentcollab_runs_per_ip_per_day=1, agentcollab_trust_proxy=True)
    for ip in ("1.1.1.1", "2.2.2.2"):
        resp = client.post(
            "/api/runs", json={"task_id": "slugify"}, headers={"X-Forwarded-For": ip}
        )
        assert resp.status_code == 202
    untrusted = make_client(agentcollab_runs_per_ip_per_day=1)
    untrusted.post("/api/runs", json={"task_id": "slugify"}, headers={"X-Forwarded-For": "3.3.3.3"})
    spoofed = untrusted.post(
        "/api/runs", json={"task_id": "slugify"}, headers={"X-Forwarded-For": "4.4.4.4"}
    )
    assert spoofed.status_code == 429


def test_daily_spending_cap(make_client):
    client = make_client(agentcollab_daily_budget_usd=0.6, agentcollab_run_budget_usd=0.5)
    first = client.post("/api/runs", json={"task_id": "slugify"}).json()["run_id"]
    collect(client, first)  # finished runs count at actual cost (~$0.02 here)
    assert client.post("/api/runs", json={"task_id": "slugify"}).status_code == 202
    tight = make_client(agentcollab_daily_budget_usd=0.4, agentcollab_run_budget_usd=0.5)
    assert tight.post("/api/runs", json={"task_id": "slugify"}).status_code == 429
