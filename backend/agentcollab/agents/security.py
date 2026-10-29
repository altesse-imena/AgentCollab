from typing import Literal

from pydantic import BaseModel

from ..llm import LLMClient, LLMResult, RunBudget
from .common import change_messages, load_prompt

PROMPT = load_prompt("security")


class Finding(BaseModel):
    path: str
    line: int | None = None
    severity: Literal["critical", "high", "medium", "low"]
    cwe: str | None = None
    issue: str
    fix: str


class SecurityReport(BaseModel):
    findings: list[Finding] = []

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.severity in ("critical", "high")]


def analyze_security(
    llm: LLMClient,
    *,
    model: str,
    task: str,
    context: dict[str, str],
    patch: str,
    changed: dict[str, str],
    budget: RunBudget,
) -> LLMResult[SecurityReport]:
    return llm.structured(
        agent="security_analyzer",
        model=model,
        schema=SecurityReport,
        budget=budget,
        messages=change_messages(PROMPT, task, context, patch, changed),
    )
