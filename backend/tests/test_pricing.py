import pytest

from agentcollab.llm.pricing import cost_usd


def test_cached_tokens_billed_at_cached_rate():
    # gpt-4.1: 800 uncached * $2 + 200 cached * $0.50 + 500 out * $8, per 1M
    assert cost_usd("gpt-4.1", 1000, 200, 500) == pytest.approx((1600 + 100 + 4000) / 1e6)


def test_unknown_model_has_no_cost():
    assert cost_usd("mystery-model", 10, 0, 10) is None
