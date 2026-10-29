from types import SimpleNamespace

import pytest

from agentcollab.config import Settings
from agentcollab.deps import MissingAPIKey, build
from agentcollab.llm.client import parse_json
from agentcollab.llm.pricing import cost_usd, price_for
from agentcollab.llm.providers import ProviderRefusal, make_provider
from agentcollab.llm.providers.anthropic import AnthropicProvider, split_system


def settings(**kw):
    return Settings(_env_file=None, **kw)


def test_model_defaults_follow_provider():
    assert settings(agentcollab_provider="openai").model_for("writer") == "gpt-4.1"
    assert settings(agentcollab_provider="anthropic").model_for("tester") == "claude-opus-5-5"


def test_role_override_beats_global_model():
    s = settings(agentcollab_model="gpt-4.1", agentcollab_model_reviewer="gpt-4.1-mini")
    assert s.model_for("reviewer") == "gpt-4.1-mini" and s.model_for("writer") == "gpt-4.1"


def test_api_key_follows_provider():
    s = settings(agentcollab_provider="anthropic", openai_api_key="o", anthropic_api_key="a")
    assert s.api_key == "a"


def test_missing_key_is_reported(tmp_path):
    with pytest.raises(MissingAPIKey, match="ANTHROPIC_API_KEY"):
        build(settings(agentcollab_provider="anthropic", database_url=f"sqlite:///{tmp_path}/x.db"))


def test_make_provider_validates():
    with pytest.raises(ValueError, match="unknown provider"):
        make_provider("nope", "k")
    with pytest.raises(ValueError, match="BASE_URL"):
        make_provider("openai_compatible", "k")


def test_dated_model_names_use_base_price():
    assert price_for("gpt-4.1-2025-04-14") == price_for("gpt-4.1")
    assert price_for("gpt-4.1-mini-2025-04-14") == price_for("gpt-4.1-mini")


def test_anthropic_cache_writes_billed_higher():
    # 1000 prompt = 600 uncached + 300 cache read + 100 cache write; 100 output
    expected = (600 * 4.00 + 300 * 0.20 + 100 * 5.00 + 100 * 20.00) / 1e6
    assert cost_usd("claude-opus-5-5", 1000, 300, 100, 100) == pytest.approx(expected)


def test_parse_json_strips_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('{"a": 1}') == {"a": 1}


def test_split_system():
    system, convo = split_system(
        [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "hi"},
        ]
    )
    assert system == "rules" and convo == [{"role": "user", "content": "hi"}]


def _fake_anthropic_response(stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        stop_details=SimpleNamespace(explanation="declined"),
        model="claude-opus-5-5",
        content=[
            SimpleNamespace(type="thinking"),
            SimpleNamespace(type="text", text='{"ok": true}'),
        ],
        usage=SimpleNamespace(
            input_tokens=50,
            cache_read_input_tokens=900,
            cache_creation_input_tokens=0,
            output_tokens=20,
        ),
    )


def test_anthropic_adapter_maps_usage_and_request():
    provider = AnthropicProvider(api_key="test")
    sent = {}

    def create(**kwargs):
        sent.update(kwargs)
        return _fake_anthropic_response()

    provider._client = SimpleNamespace(
        beta=SimpleNamespace(messages=SimpleNamespace(create=create))
    )
    resp = provider.chat(
        "claude-opus-5-5",
        [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "hi"},
        ],
        json_mode=True,
    )
    assert resp.text == '{"ok": true}'
    assert (resp.prompt_tokens, resp.cached_tokens, resp.completion_tokens) == (950, 900, 20)
    assert sent["system"] == "rules" and sent["fallbacks"] == "default"
    assert sent["messages"] == [{"role": "user", "content": "hi"}]


def test_anthropic_refusal_raises():
    provider = AnthropicProvider(api_key="test")
    provider._client = SimpleNamespace(
        beta=SimpleNamespace(
            messages=SimpleNamespace(create=lambda **_: _fake_anthropic_response("refusal"))
        )
    )
    with pytest.raises(ProviderRefusal, match="declined"):
        provider.chat("claude-opus-5-5", [{"role": "user", "content": "x"}], json_mode=True)
