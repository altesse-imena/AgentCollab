import operator
from typing import Annotated, Literal, TypedDict

Status = Literal["running", "passed", "failed", "aborted"]


def merge(a: dict | None, b: dict | None) -> dict:
    """Merge parallel agents' updates. Writing None clears the dict (done at each new round)."""
    return {} if b is None else {**(a or {}), **b}


class RunState(TypedDict, total=False):
    # Inputs
    run_id: str
    task: str
    repo_path: str
    max_iterations: int
    budget_usd: float

    # Working state
    context: dict[str, str]
    iteration: int
    change: dict | None  # CodeChange as a dict: {"summary", "files": [{"path", "content"}]}
    patch: str
    review: dict | None
    security: dict | None
    tests: dict | None
    test_result: dict | None
    feedback: str | None

    # Written by parallel agents, so these need reducers
    spent_usd: Annotated[float, operator.add]
    agent_errors: Annotated[dict[str, str], merge]
    history: Annotated[list[dict], operator.add]

    # Outcome
    status: Status
    error: str | None
