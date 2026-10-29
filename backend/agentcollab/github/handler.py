"""Turns a labeled GitHub issue into an AgentCollab run and, if it passes, a draft PR."""

import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..repo import apply_files
from ..service import RunOutcome


@dataclass
class IssueJob:
    repo: str  # owner/name
    issue: int
    title: str
    body: str
    default_branch: str
    installation_id: int


def job_from_event(event: str, payload: dict, label: str) -> IssueJob | None:
    """Only 'issues' events where our label was just added start a job."""
    if event != "issues" or payload.get("action") != "labeled":
        return None
    if (payload.get("label") or {}).get("name") != label:
        return None
    issue, repo = payload["issue"], payload["repository"]
    if issue.get("pull_request"):
        return None
    return IssueJob(
        repo=repo["full_name"],
        issue=issue["number"],
        title=issue["title"],
        body=issue.get("body") or "",
        default_branch=repo["default_branch"],
        installation_id=payload["installation"]["id"],
    )


def task_text(job: IssueJob) -> str:
    return f"Resolve GitHub issue #{job.issue}: {job.title}\n\n{job.body}".strip()


def pr_body(job: IssueJob, outcome: RunOutcome, run_url: str | None) -> str:
    lines = [
        f"Fixes #{job.issue}",
        "",
        f"**Summary:** {outcome.summary}",
        "",
        f"Tests, code review and security analysis passed after {outcome.iterations} "
        f"round(s), costing ${outcome.spent_usd:.4f}.",
    ]
    if run_url:
        lines += ["", f"[Watch the agents' run]({run_url})"]
    lines += ["", "_Opened as a draft by AgentCollab. A human should review before merging._"]
    return "\n".join(lines)


def handle_issue(
    job: IssueJob,
    *,
    app,
    git_factory: Callable[[str], object],
    run: Callable[[str, Path], RunOutcome],
    public_url: str | None = None,
) -> str:
    """Clone, run the agents, and report back on the issue. Returns what happened."""
    token = app.installation_token(job.installation_id)
    git = git_factory(token)
    with tempfile.TemporaryDirectory(prefix="agentcollab-gh-") as tmp:
        workdir = Path(tmp) / "repo"
        git.clone(job.repo, workdir, job.default_branch)
        outcome = run(task_text(job), workdir)
        run_url = f"{public_url.rstrip('/')}/#/runs/{outcome.run_id}" if public_url else None

        if outcome.status != "passed":
            app.comment(
                token,
                job.repo,
                job.issue,
                f"AgentCollab couldn't produce a passing change ({outcome.status}: "
                f"{outcome.error}). Cost ${outcome.spent_usd:.4f}."
                + (f" [See the run]({run_url})." if run_url else ""),
            )
            return "commented: no passing change"

        branch = f"agentcollab/issue-{job.issue}-{outcome.run_id[:8]}"
        apply_files(workdir, outcome.files)
        git.commit_and_push(workdir, branch, f"Resolve #{job.issue}: {job.title}")
        pr = app.create_pull_request(
            token, job.repo, branch, job.default_branch,
            f"AgentCollab: {job.title}", pr_body(job, outcome, run_url),
        )  # fmt: skip
        app.comment(token, job.repo, job.issue, f"Opened draft PR {pr['html_url']} for this issue.")
        return f"opened {pr['html_url']}"
