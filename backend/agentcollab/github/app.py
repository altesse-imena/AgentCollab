"""GitHub App client: authenticates as an installation and talks to the REST API and git."""

import base64
import hashlib
import hmac
import os
import subprocess
import time
from pathlib import Path

import httpx
import jwt

API = "https://api.github.com"
BOT_EMAIL = "agentcollab@users.noreply.github.com"


def verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    """Check GitHub's X-Hub-Signature-256 header (HMAC-SHA256 of the raw body)."""
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


class GitHubApp:
    def __init__(self, app_id: str, private_key: str, http: httpx.Client | None = None):
        self.app_id = app_id
        self.private_key = private_key
        self.http = http or httpx.Client(base_url=API, timeout=30)

    def _app_jwt(self) -> str:
        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 540, "iss": self.app_id}
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def installation_token(self, installation_id: int) -> str:
        resp = self.http.post(
            f"/app/installations/{installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {self._app_jwt()}", **_json_headers()},
        )
        resp.raise_for_status()
        return resp.json()["token"]

    def _api(self, method: str, path: str, token: str, **kwargs) -> dict:
        resp = self.http.request(
            method, path, headers={"Authorization": f"Bearer {token}", **_json_headers()}, **kwargs
        )
        resp.raise_for_status()
        return resp.json()

    def create_pull_request(
        self, token: str, repo: str, head: str, base: str, title: str, body: str
    ) -> dict:
        return self._api(
            "POST",
            f"/repos/{repo}/pulls",
            token,
            json={"title": title, "head": head, "base": base, "body": body, "draft": True},
        )

    def comment(self, token: str, repo: str, issue: int, body: str) -> dict:
        return self._api(
            "POST", f"/repos/{repo}/issues/{issue}/comments", token, json={"body": body}
        )


def _json_headers() -> dict:
    return {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


class Git:
    """Runs git with the installation token passed as a header through the environment,
    so it never appears in process arguments, remotes or logs."""

    def __init__(self, token: str):
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        self.env = {
            **os.environ,
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {basic}",
            "GIT_TERMINAL_PROMPT": "0",
        }

    def run(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run(
            ["git", *args], cwd=cwd, env=self.env, check=True, capture_output=True, text=True
        ).stdout

    def clone(self, repo: str, dest: Path, branch: str) -> None:
        self.run("clone", "--depth", "1", "--branch", branch, f"https://github.com/{repo}.git",
                 str(dest))  # fmt: skip

    def commit_and_push(self, workdir: Path, branch: str, message: str) -> None:
        self.run("checkout", "-b", branch, cwd=workdir)
        self.run("add", "-A", cwd=workdir)
        identity = ["-c", "user.name=agentcollab[bot]", "-c", f"user.email={BOT_EMAIL}"]
        self.run(*identity, "commit", "-m", message, cwd=workdir)
        self.run("push", "origin", branch, cwd=workdir)
