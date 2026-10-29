from pydantic import BaseModel, Field, field_validator

from ..llm import LLMClient, LLMResult, RunBudget
from .common import change_messages, load_prompt
from .writer import FileEdit

PROMPT = load_prompt("tester")


class TestSuite(BaseModel):
    __test__ = False  # not a pytest class

    files: list[FileEdit] = Field(min_length=1)

    @field_validator("files")
    @classmethod
    def tests_only(cls, files: list[FileEdit]) -> list[FileEdit]:
        for f in files:
            name = f.path.rsplit("/", 1)[-1]
            if not f.path.startswith("tests/") or not name.startswith("test_"):
                raise ValueError(f"test files must be tests/test_*.py, got {f.path!r}")
        return files


def generate_tests(
    llm: LLMClient,
    *,
    model: str,
    task: str,
    context: dict[str, str],
    patch: str,
    changed: dict[str, str],
    budget: RunBudget,
) -> LLMResult[TestSuite]:
    return llm.structured(
        agent="test_generator",
        model=model,
        schema=TestSuite,
        budget=budget,
        messages=change_messages(PROMPT, task, context, patch, changed),
    )
