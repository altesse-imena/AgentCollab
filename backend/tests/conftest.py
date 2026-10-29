import json
import threading

import pytest

from agentcollab.db import make_engine, make_recorder
from agentcollab.graph import Deps
from agentcollab.llm import LLMClient, ProviderResponse
from agentcollab.sandbox import TestResult


def _response(item):
    if isinstance(item, Exception):
        raise item
    text = item if isinstance(item, str) else json.dumps(item)
    return ProviderResponse(text=text, prompt_tokens=1000, cached_tokens=200, completion_tokens=500)


class FakeProvider:
    """Plays back scripted replies in order. An Exception in the script is raised instead."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def chat(self, model, messages, json_mode):
        self.calls.append({"model": model, "messages": messages})
        return _response(self.script.pop(0))


ROLE_BY_PROMPT = {
    "You are CodeWriter": "writer",
    "You are CodeReviewer": "reviewer",
    "You are TestGenerator": "tester",
    "You are SecurityAnalyzer": "security",
}


class RoleFakeProvider:
    """Replies per agent role, so parallel agents get the right script whatever order they run.
    A role's last reply repeats once its script runs out."""

    def __init__(self, scripts: dict[str, list]):
        self.scripts = {role: list(items) for role, items in scripts.items()}
        self.calls: list[dict] = []
        self._lock = threading.Lock()

    def chat(self, model, messages, json_mode):
        system = messages[0]["content"]
        role = next(r for prefix, r in ROLE_BY_PROMPT.items() if system.startswith(prefix))
        with self._lock:
            self.calls.append({"role": role, "model": model, "messages": messages})
            script = self.scripts[role]
            item = script.pop(0) if len(script) > 1 else script[0]
        return _response(item)

    def for_role(self, role):
        return [c for c in self.calls if c["role"] == role]


class FakeSandbox:
    def __init__(self, results: list[bool]):
        self.results = list(results)
        self.workspaces: list[dict[str, str]] = []

    def run_tests(self, workspace):
        files = {
            p.relative_to(workspace).as_posix(): p.read_text()
            for p in workspace.rglob("*")
            if p.is_file()
        }
        self.workspaces.append(files)
        passed = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        output = (
            "3 passed" if passed else "FAILED tests/test_agentcollab_x.py::test_x - assert 1 == 2"
        )
        return TestResult(passed=passed, exit_code=0 if passed else 1, output=output, duration_ms=5)


@pytest.fixture
def engine(tmp_path):
    return make_engine(f"sqlite:///{tmp_path / 'test.db'}")


@pytest.fixture
def make_llm(engine):
    def _make(script):
        provider = FakeProvider(script)
        return LLMClient(provider, recorder=make_recorder(engine), wait_max_s=0), provider

    return _make


@pytest.fixture
def make_deps(engine):
    def _make(scripts, sandbox_results=(True,)):
        provider = RoleFakeProvider(scripts)
        sandbox = FakeSandbox(list(sandbox_results))
        llm = LLMClient(provider, recorder=make_recorder(engine), wait_max_s=0)
        return Deps(llm=llm, sandbox=sandbox, model_for=lambda role: "gpt-4.1"), provider, sandbox

    return _make
