import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from agentcollab.db import LLMCall
from agentcollab.llm import BudgetExceeded, InvalidModelOutput, RunBudget
from agentcollab.llm.providers import TransientProviderError


class Answer(BaseModel):
    value: int


def ask(llm, budget=None):
    return llm.structured(
        agent="test",
        model="gpt-4.1",
        messages=[{"role": "user", "content": "hi"}],
        schema=Answer,
        budget=budget or RunBudget("r1", limit_usd=1.0),
    )


def test_valid_reply_is_parsed_and_logged(make_llm, engine):
    llm, _ = make_llm([{"value": 7}])
    result = ask(llm)
    assert result.output.value == 7
    with Session(engine) as s:
        rows = s.scalars(select(LLMCall)).all()
    assert len(rows) == 1 and rows[0].cost_usd == pytest.approx(0.0057)


def test_transient_errors_are_retried(make_llm):
    llm, provider = make_llm(
        [TransientProviderError("429"), TransientProviderError("503"), {"value": 1}]
    )
    assert ask(llm).output.value == 1
    assert len(provider.calls) == 3


def test_retries_give_up_after_max_attempts(make_llm):
    llm, _ = make_llm([TransientProviderError("429")] * 6)
    with pytest.raises(TransientProviderError):
        ask(llm)


def test_malformed_reply_gets_one_repair_attempt(make_llm):
    llm, provider = make_llm(["not json", {"value": 2}])
    result = ask(llm)
    assert result.output.value == 2
    assert [c.attempt for c in result.calls] == [1, 2]
    assert "not valid JSON" in provider.calls[1]["messages"][-1]["content"]


def test_two_malformed_replies_fail(make_llm):
    llm, _ = make_llm(["nope", {"wrong": "shape"}])
    with pytest.raises(InvalidModelOutput):
        ask(llm)


def test_budget_stops_new_calls(make_llm):
    llm, provider = make_llm([{"value": 1}, {"value": 2}])
    budget = RunBudget("r1", limit_usd=0.005)
    ask(llm, budget)  # spends ~$0.0057, over the limit
    with pytest.raises(BudgetExceeded):
        ask(llm, budget)
    assert len(provider.calls) == 1


class MemoryCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, model, text):
        self.data[key] = text


def test_response_cache_answers_repeat_requests_for_free(engine):
    from agentcollab.db import DbResponseCache
    from agentcollab.db.session import make_recorder
    from agentcollab.llm import LLMClient
    from tests.conftest import FakeProvider

    provider = FakeProvider([{"value": 5}])
    llm = LLMClient(provider, recorder=make_recorder(engine), wait_max_s=0,
                    cache=DbResponseCache(engine))  # fmt: skip
    first, second = ask(llm), ask(llm)
    assert first.output.value == second.output.value == 5
    assert len(provider.calls) == 1
    assert second.calls[0].cache_hit and second.calls[0].cost_usd == 0.0
    with Session(engine) as s:
        assert [r.cache_hit for r in s.scalars(select(LLMCall))] == [False, True]


def test_invalid_replies_are_not_cached(engine):
    from agentcollab.llm import LLMClient
    from tests.conftest import FakeProvider

    cache = MemoryCache()
    llm = LLMClient(FakeProvider(["nope", {"value": 1}]), wait_max_s=0, cache=cache)
    ask(llm)
    assert list(cache.data.values()) == ['{"value": 1}']  # stored under the original request


def test_cached_reply_that_no_longer_fits_schema_is_ignored():
    from agentcollab.llm import LLMClient
    from agentcollab.llm.client import cache_key
    from tests.conftest import FakeProvider

    cache = MemoryCache()
    cache.data[cache_key("gpt-4.1", [{"role": "user", "content": "hi"}])] = '{"old": 1}'
    provider = FakeProvider([{"value": 3}])
    assert ask(LLMClient(provider, wait_max_s=0, cache=cache)).output.value == 3
    assert len(provider.calls) == 1


def test_backoff_waits_for_retry_after_hint():
    from tenacity import RetryCallState

    from agentcollab.llm.client import MAX_RETRY_AFTER_S, backoff

    def state_with(error):
        state = RetryCallState(retry_object=None, fn=None, args=(), kwargs={})
        state.attempt_number = 1
        state.set_exception((type(error), error, None))
        return state

    wait = backoff(wait_max_s=20)
    assert wait(state_with(TransientProviderError("429", retry_after_s=30))) == 30
    assert wait(state_with(TransientProviderError("429", retry_after_s=600))) == MAX_RETRY_AFTER_S
    assert wait(state_with(TransientProviderError("503"))) == 1  # plain exponential backoff
    assert backoff(wait_max_s=0)(state_with(TransientProviderError("429", 30))) == 0


def test_long_waits_are_not_retried(make_llm):
    from agentcollab.llm.client import QuotaExhausted

    daily = TransientProviderError("tokens per day. Please try again in 6m8.5s.", 368.5)
    llm, provider = make_llm([daily, {"value": 1}])
    with pytest.raises(QuotaExhausted, match="wait 6 min"):
        ask(llm)


def test_retry_hint_is_read_from_the_message():
    from agentcollab.llm.providers.base import retry_after_s

    assert retry_after_s(Exception("Please try again in 6m8.5s.")) == 368.5
    assert retry_after_s(Exception("try again in 1h2m")) == 3720
    assert retry_after_s(Exception("server busy")) is None
