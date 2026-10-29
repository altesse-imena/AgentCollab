import hashlib
import hmac
import json
import subprocess
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from agentcollab.config import Settings
from agentcollab.github import Git, GitHubApp, handle_issue, job_from_event, verify_signature
from agentcollab.main import create_app
from tests.test_api import fake_factory

SECRET = "s3cret"


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def labeled(label="agentcollab", **issue):
    return {
        "action": "labeled",
        "label": {"name": label},
        "issue": {"number": 7, "title": "Add greet", "body": "Please add greet()", **issue},
        "repository": {"full_name": "me/demo", "default_branch": "main"},
        "installation": {"id": 99},
    }


def test_signature():
    body = b'{"a":1}'
    assert verify_signature(SECRET, body, sign(body))
    assert not verify_signature(SECRET, body, sign(b"other"))
    assert not verify_signature(SECRET, body, None)


def test_only_our_label_on_issues_starts_a_job():
    assert job_from_event("issues", labeled(), "agentcollab").repo == "me/demo"
    assert job_from_event("issues", labeled("bug"), "agentcollab") is None
    assert job_from_event("push", labeled(), "agentcollab") is None
    assert job_from_event("issues", {**labeled(), "action": "opened"}, "agentcollab") is None
    pr = labeled(pull_request={"url": "x"})
    assert job_from_event("issues", pr, "agentcollab") is None


def test_app_jwt_is_signed_for_the_app():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    token = GitHubApp("123", pem)._app_jwt()
    claims = jwt.decode(token, key.public_key(), algorithms=["RS256"])
    assert claims["iss"] == "123" and claims["exp"] - claims["iat"] <= 600


class FakeApp:
    def __init__(self):
        self.comments, self.prs = [], []

    def installation_token(self, installation_id):
        assert installation_id == 99
        return "tok"

    def comment(self, token, repo, issue, body):
        self.comments.append((repo, issue, body))

    def create_pull_request(self, token, repo, head, base, title, body):
        self.prs.append({"repo": repo, "head": head, "base": base, "title": title, "body": body})
        return {"html_url": "https://github.com/me/demo/pull/8"}


class FakeGit:
    def __init__(self, token):
        self.token, self.pushed = token, None

    def clone(self, repo, dest, branch):
        dest.mkdir(parents=True)
        (dest / "app.py").write_text("x = 1\n")

    def commit_and_push(self, workdir, branch, message):
        self.pushed = (branch, message, (workdir / "app.py").read_text())


def outcome(status="passed"):
    return SimpleNamespace(
        run_id="abcdef1234", status=status, summary="added greet", iterations=2,
        spent_usd=0.03, error=None if status == "passed" else "did not pass",
        files={"app.py": "def greet(): ...\n"},
    )  # fmt: skip


def test_passing_run_opens_a_draft_pr():
    app, gits, tasks = FakeApp(), [], []

    def git_factory(token):
        gits.append(FakeGit(token))
        return gits[-1]

    def run(task, workdir):
        tasks.append(task)
        assert (workdir / "app.py").exists()  # ran on the cloned repo
        return outcome()

    job = job_from_event("issues", labeled(), "agentcollab")
    result = handle_issue(job, app=app, git_factory=git_factory, run=run,
                          public_url="https://demo.example")  # fmt: skip
    assert result.endswith("/pull/8")
    assert "Add greet" in tasks[0] and "Please add greet()" in tasks[0]
    branch, message, content = gits[0].pushed
    assert branch == "agentcollab/issue-7-abcdef12" and content == "def greet(): ...\n"
    pr = app.prs[0]
    assert pr["base"] == "main" and "Fixes #7" in pr["body"]
    assert "https://demo.example/#/runs/abcdef1234" in pr["body"]
    assert "pull/8" in app.comments[0][2]


def test_failing_run_only_comments():
    app, git = FakeApp(), FakeGit("tok")
    job = job_from_event("issues", labeled(), "agentcollab")
    handle_issue(job, app=app, git_factory=lambda t: git, run=lambda *_: outcome("failed"))
    assert app.prs == [] and git.pushed is None
    assert "couldn't produce a passing change" in app.comments[0][2]


def test_git_keeps_token_out_of_arguments_and_pushes(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    (work / "a.txt").write_text("a")
    git = Git("ghs_secret")
    assert all("ghs_secret" not in v for k, v in git.env.items() if not k.startswith("GIT_CONFIG"))
    git.commit_and_push(work, "agentcollab/x", "msg")
    log = subprocess.run(["git", "--git-dir", str(origin), "log", "--format=%an %s",
                          "agentcollab/x"], capture_output=True, text=True).stdout  # fmt: skip
    assert log.strip() == "agentcollab[bot] msg"


@pytest.fixture
def client(tmp_path):
    jobs = []
    s = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'gh.db'}",
        github_app_id="1",
        github_app_private_key="x",
        github_webhook_secret=SECRET,
    )
    c = TestClient(create_app(s, deps_factory=fake_factory, on_issue=jobs.append))
    c.jobs = jobs
    return c


def post(client, payload, event="issues", signature=None):
    body = json.dumps(payload).encode()
    headers = {"X-GitHub-Event": event, "X-Hub-Signature-256": signature or sign(body),
               "Content-Type": "application/json"}  # fmt: skip
    return client.post("/api/github/webhook", content=body, headers=headers)


def test_webhook_starts_a_job(client):
    resp = post(client, labeled())
    assert resp.status_code == 202 and resp.json()["accepted"]
    client.app.state.pool.shutdown(wait=True)
    assert client.jobs[0].issue == 7


def test_webhook_rejects_bad_signature(client):
    assert post(client, labeled(), signature="sha256=bad").status_code == 401


def test_webhook_ignores_other_events(client):
    assert post(client, labeled("bug")).json() == {"accepted": False}


def test_webhook_off_when_not_configured(tmp_path):
    s = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'x.db'}")
    c = TestClient(create_app(s, deps_factory=fake_factory))
    assert c.post("/api/github/webhook", content=b"{}").status_code == 404
