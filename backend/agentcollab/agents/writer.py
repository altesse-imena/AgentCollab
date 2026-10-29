from pydantic import BaseModel, Field

from ..llm import LLMClient, LLMResult, RunBudget
from .common import load_prompt, render_files

PROMPT = load_prompt("writer")


class FileEdit(BaseModel):
    path: str
    content: str


class CodeChange(BaseModel):
    summary: str
    files: list[FileEdit] = Field(min_length=1)


def build_messages(task: str, context: dict[str, str], feedback: str | None) -> list[dict]:
    # Unchanging content first, so the provider's prompt cache can reuse it across rounds
    repo = render_files(context)
    user = f"# Repository files\n\n{repo or '(empty repository)'}\n\n# Task\n\n{task}"
    if feedback:
        user += f"\n\n# Feedback on your previous attempt\n\n{feedback}"
    return [{"role": "system", "content": PROMPT}, {"role": "user", "content": user}]


def write_code(
    llm: LLMClient,
    *,
    model: str,
    task: str,
    context: dict[str, str],
    budget: RunBudget,
    feedback: str | None = None,
) -> LLMResult[CodeChange]:
    return llm.structured(
        agent="code_writer",
        model=model,
        messages=build_messages(task, context, feedback),
        schema=CodeChange,
        budget=budget,
    )
