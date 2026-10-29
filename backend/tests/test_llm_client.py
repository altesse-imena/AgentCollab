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
        agent="test", model="gpt-4.1", messages=[{"role": "user", "content": "hi"}],
        schema=Answer, budget=budget or RunBudget("r1", limit_usd=1.0),
    )


def test_valid_reply_is_parsed_and_logged(make_llm, engine):
    llm, _ = make_llm([{"value": 7}])
    result = ask(llm)
    assert result.output.value == 7
    with Session(engine) as s:
        rows = s.scalars(select(LLMCall)).all()
    assert len(rows) == 1 and rows[0].cost_usd == pytest.approx(0.0057)


def test_transient_errors_are_retried(make_llm):
    llm, provider = make_llm([TransientProviderError("429"), TransientProviderError("503"), {"value": 1}])
    assert ask(llm).output.value == 1
    assert len(provider.calls) == 3


def test_retries_give_up_after_max_attempts(make_llm):
    llm, _ = make_llm([TransientProviderError("429")] * 4)
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
