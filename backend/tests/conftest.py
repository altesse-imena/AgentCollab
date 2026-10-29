import json

import pytest

from agentcollab.db import make_engine, make_recorder
from agentcollab.llm import LLMClient, ProviderResponse


class FakeProvider:
    """Plays back scripted replies. An Exception in the script is raised instead."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def chat(self, model, messages, json_mode):
        self.calls.append({"model": model, "messages": messages})
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        text = item if isinstance(item, str) else json.dumps(item)
        return ProviderResponse(text=text, prompt_tokens=1000, cached_tokens=200, completion_tokens=500)


@pytest.fixture
def engine(tmp_path):
    return make_engine(f"sqlite:///{tmp_path / 'test.db'}")


@pytest.fixture
def make_llm(engine):
    def _make(script):
        provider = FakeProvider(script)
        return LLMClient(provider, recorder=make_recorder(engine), wait_max_s=0), provider

    return _make
