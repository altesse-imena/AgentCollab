"""The AgentCollab workflow.

gather_context -> write -> (review | tests | security) -> run_tests -> judge
                    ^                                                  |
                    +----------- feedback (max_iterations) ------------+
"""

import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from ..agents import analyze_security, generate_tests, review_code, write_code
from ..llm import BudgetExceeded, InvalidModelOutput, LLMClient, ProviderRefusal, RunBudget
from ..llm.providers import TransientProviderError
from ..repo import gather_context, make_patch, safe_path
from ..repo.files import UnsafePath
from ..sandbox import Sandbox, build_workspace
from .feedback import build_feedback, is_passing
from .state import RunState

# Errors an agent can hit that should fail that agent, not crash the whole run
AGENT_ERRORS = (InvalidModelOutput, ProviderRefusal, TransientProviderError, UnsafePath)


@dataclass
class Deps:
    llm: LLMClient
    sandbox: Sandbox
    model_for: Callable[[str], str]


def _budget(state: RunState) -> RunBudget:
    return RunBudget(state["run_id"], state["budget_usd"], state.get("spent_usd", 0.0))


def _spent(budget: RunBudget, before: float) -> float:
    return budget.spent_usd - before


def build_graph(deps: Deps, checkpointer=None):
    def gather(state: RunState) -> dict:
        return {
            "context": gather_context(Path(state["repo_path"])),
            "iteration": 0,
            "spent_usd": 0.0,
            "agent_errors": {},
            "history": [],
            "status": "running",
            "error": None,
        }

    def write(state: RunState) -> dict:
        budget = _budget(state)
        before = budget.spent_usd
        iteration = state["iteration"] + 1
        base = {"iteration": iteration, "agent_errors": None, "review": None, "security": None,
                "tests": None, "test_result": None}  # fmt: skip
        try:
            result = write_code(
                deps.llm, model=deps.model_for("writer"), task=state["task"],
                context=state["context"], budget=budget, feedback=state.get("feedback"),
            )  # fmt: skip
            repo = Path(state["repo_path"])
            files = {}
            for edit in result.output.files:
                safe_path(repo, edit.path)
                files[edit.path] = edit.content
        except BudgetExceeded as e:
            return {**base, "status": "aborted", "error": str(e),
                    "spent_usd": _spent(budget, before)}  # fmt: skip
        except AGENT_ERRORS as e:
            return {**base, "status": "failed", "error": f"code_writer: {e}",
                    "spent_usd": _spent(budget, before)}  # fmt: skip
        return {
            **base,
            "change": result.output.model_dump(),
            "patch": make_patch(state["context"], files),
            "spent_usd": _spent(budget, before),
        }

    def after_write(state: RunState) -> list[str] | str:
        return "finalize" if state["status"] != "running" else ["review", "tests", "security"]

    def _changed(state: RunState) -> dict[str, str]:
        return {f["path"]: f["content"] for f in state["change"]["files"]}

    def _parallel_agent(name: str, key: str, fn, role: str):
        def node(state: RunState) -> dict:
            budget = _budget(state)
            before = budget.spent_usd
            try:
                result = fn(
                    deps.llm, model=deps.model_for(role), task=state["task"],
                    context=state["context"], patch=state["patch"], changed=_changed(state),
                    budget=budget,
                )  # fmt: skip
            except (BudgetExceeded, *AGENT_ERRORS) as e:
                # One agent failing doesn't stop the round; the judge works with what arrived
                return {"agent_errors": {name: str(e)}, "spent_usd": _spent(budget, before)}
            return {key: result.output.model_dump(), "spent_usd": _spent(budget, before)}

        return node

    def run_tests(state: RunState) -> dict:
        files = _changed(state)
        for f in (state.get("tests") or {}).get("files", []):
            files[f["path"]] = f["content"]
        with tempfile.TemporaryDirectory(prefix="agentcollab-") as tmp:
            workspace = build_workspace(Path(state["repo_path"]), Path(tmp) / "ws", files)
            result = deps.sandbox.run_tests(workspace)
        return {"test_result": result.model_dump()}

    def judge(state: RunState) -> dict:
        passed = is_passing(state)
        record = {
            "iteration": state["iteration"],
            "passed": passed,
            "tests_passed": bool(state["test_result"] and state["test_result"]["passed"]),
            "agent_errors": state.get("agent_errors", {}),
        }
        if passed:
            return {"status": "passed", "history": [record]}
        if state.get("spent_usd", 0.0) >= state["budget_usd"]:
            return {"status": "aborted", "error": "budget exhausted", "history": [record]}
        if state["iteration"] >= state["max_iterations"]:
            return {
                "status": "failed",
                "error": f"did not pass after {state['iteration']} rounds",
                "history": [record],
            }
        return {"feedback": build_feedback(state), "history": [record]}

    def after_judge(state: RunState) -> str:
        return "write" if state["status"] == "running" else "finalize"

    def finalize(state: RunState) -> dict:
        return {}

    g = StateGraph(RunState)
    g.add_node("gather_context", gather)
    g.add_node("write", write)
    g.add_node("review", _parallel_agent("code_reviewer", "review", review_code, "reviewer"))
    g.add_node("tests", _parallel_agent("test_generator", "tests", generate_tests, "tester"))
    g.add_node(
        "security", _parallel_agent("security_analyzer", "security", analyze_security, "security")
    )
    g.add_node("run_tests", run_tests)
    g.add_node("judge", judge)
    g.add_node("finalize", finalize)

    g.add_edge(START, "gather_context")
    g.add_edge("gather_context", "write")
    g.add_conditional_edges("write", after_write, ["review", "tests", "security", "finalize"])
    g.add_edge(["review", "tests", "security"], "run_tests")  # waits for all three
    g.add_edge("run_tests", "judge")
    g.add_conditional_edges("judge", after_judge, ["write", "finalize"])
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)
