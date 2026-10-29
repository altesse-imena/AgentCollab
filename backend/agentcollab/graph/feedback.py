"""Turns one round's results into a verdict and, if needed, feedback for CodeWriter."""

from ..agents import Review, SecurityReport
from ..sandbox import TestResult
from .state import RunState


def blocking_issues(state: RunState) -> tuple[list[str], list[str], TestResult | None]:
    review = Review.model_validate(state["review"]) if state.get("review") else None
    security = SecurityReport.model_validate(state["security"]) if state.get("security") else None
    result = TestResult.model_validate(state["test_result"]) if state.get("test_result") else None
    review_issues = [
        f"[{c.severity}] {c.path}{f':{c.line}' if c.line else ''}: {c.message}"
        for c in (review.blocking if review else [])
    ]
    security_issues = [
        f"[{f.severity}{f' {f.cwe}' if f.cwe else ''}] {f.path}{f':{f.line}' if f.line else ''}: "
        f"{f.issue} Fix: {f.fix}"
        for f in (security.blocking if security else [])
    ]
    return review_issues, security_issues, result


def is_passing(state: RunState) -> bool:
    review_issues, security_issues, result = blocking_issues(state)
    return bool(result and result.passed) and not review_issues and not security_issues


def build_feedback(state: RunState) -> str:
    review_issues, security_issues, result = blocking_issues(state)
    parts = []
    if result and not result.passed:
        parts.append(f"## Test run failed\n\n```\n{result.output[-4000:]}\n```")
    if review_issues:
        parts.append("## Code review\n\n" + "\n".join(f"- {i}" for i in review_issues))
    if security_issues:
        parts.append("## Security\n\n" + "\n".join(f"- {i}" for i in security_issues))
    if not parts:
        parts.append("The previous attempt did not pass. Re-check the task requirements.")
    return "\n\n".join(parts)
