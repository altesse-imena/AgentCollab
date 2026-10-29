from typing import Literal

from pydantic import BaseModel

from ..llm import LLMClient, LLMResult, RunBudget
from .common import change_messages, load_prompt

PROMPT = load_prompt("reviewer")


class ReviewComment(BaseModel):
    path: str
    line: int | None = None
    severity: Literal["blocker", "major", "minor", "nit"]
    message: str


class Review(BaseModel):
    approved: bool
    comments: list[ReviewComment] = []

    @property
    def blocking(self) -> list[ReviewComment]:
        return [c for c in self.comments if c.severity in ("blocker", "major")]


def review_code(
    llm: LLMClient,
    *,
    model: str,
    task: str,
    context: dict[str, str],
    patch: str,
    changed: dict[str, str],
    budget: RunBudget,
) -> LLMResult[Review]:
    return llm.structured(
        agent="code_reviewer",
        model=model,
        schema=Review,
        budget=budget,
        messages=change_messages(PROMPT, task, context, patch, changed),
    )
