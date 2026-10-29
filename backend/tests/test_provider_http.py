"""Run the real SDKs against mocked HTTP, so request building and response parsing are
checked end to end without an API key."""

import json

import httpx
import httpx2
import pytest

from agentcollab.llm.providers import ProviderRefusal, TransientProviderError
from agentcollab.llm.providers.anthropic import AnthropicProvider
from agentcollab.llm.providers.openai import OpenAIProvider

MESSAGES = [{"role": "system", "content": "rules"}, {"role": "user", "content": "hi"}]


def mock(handler, lib=httpx):
    """A client whose requests go to `handler`. The Anthropic SDK uses httpx2, OpenAI httpx."""
    sent = []

    def wrapped(request):
        sent.append(request)
        status, body = handler(request)
        return lib.Response(status, json=body)

    return lib.Client(transport=lib.MockTransport(wrapped)), sent


def openai_completion(request):
    return (
        200,
        {
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 1,
            "model": "gpt-4.1-2025-04-14",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": '{"ok": true}'},
                }
            ],
            "usage": {
                "prompt_tokens": 1200,
                "completion_tokens": 50,
                "total_tokens": 1250,
                "prompt_tokens_details": {"cached_tokens": 1024},
            },
        },
    )


def test_openai_request_and_usage():
    http, sent = mock(openai_completion)
    resp = OpenAIProvider("sk-test", http_client=http).chat("gpt-4.1", MESSAGES, json_mode=True)
    body = json.loads(sent[0].content)
    assert sent[0].url.path.endswith("/chat/completions")
    assert sent[0].headers["authorization"] == "Bearer sk-test"
    assert body["response_format"] == {"type": "json_object"} and body["messages"] == MESSAGES
    assert (resp.text, resp.prompt_tokens, resp.cached_tokens, resp.completion_tokens) == (
        '{"ok": true}', 1200, 1024, 50,
    )  # fmt: skip
    assert resp.model == "gpt-4.1-2025-04-14"


def test_openai_compatible_base_url():
    http, sent = mock(openai_completion)
    OpenAIProvider("k", base_url="https://openrouter.ai/api/v1", http_client=http).chat(
        "some/model", MESSAGES, json_mode=True
    )
    assert str(sent[0].url) == "https://openrouter.ai/api/v1/chat/completions"


@pytest.mark.parametrize("status", [429, 500, 503])
def test_openai_retryable_errors(status):
    http, _ = mock(lambda r: (status, {"error": {"message": "busy"}}))
    with pytest.raises(TransientProviderError):
        OpenAIProvider("k", http_client=http).chat("gpt-4.1", MESSAGES, json_mode=True)


def anthropic_message(stop_reason="end_turn"):
    def handler(request):
        return (
            200,
            {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5-5",
                "content": [{"type": "text", "text": '{"ok": true}'}],
                "stop_reason": stop_reason,
                "stop_sequence": None,
                "stop_details": {"type": "refusal", "category": "cyber", "explanation": "no"}
                if stop_reason == "refusal"
                else None,
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 40,
                    "cache_read_input_tokens": 2000,
                    "cache_creation_input_tokens": 300,
                },
            },
        )

    return handler


def test_anthropic_request_and_usage():
    http, sent = mock(anthropic_message(), httpx2)
    resp = AnthropicProvider("sk-ant-test", http_client=http).chat(
        "claude-opus-5-5", MESSAGES, json_mode=True
    )
    body = json.loads(sent[0].content)
    assert sent[0].url.path == "/v1/messages"
    assert "sk-ant-test" in (sent[0].headers.get("x-api-key") or sent[0].headers["authorization"])
    assert "server-side-fallback-2026-07-01" in sent[0].headers["anthropic-beta"]
    assert body["system"] == "rules" and body["messages"] == MESSAGES[1:]
    assert body["fallbacks"] == "default" and body["cache_control"] == {"type": "ephemeral"}
    assert body["max_tokens"] == 16000
    assert (resp.prompt_tokens, resp.cached_tokens, resp.cache_write_tokens) == (2400, 2000, 300)
    assert resp.text == '{"ok": true}'


def test_anthropic_models_without_fallback_use_plain_endpoint():
    http, sent = mock(anthropic_message(), httpx2)
    AnthropicProvider("k", http_client=http).chat("claude-haiku-5-5", MESSAGES, json_mode=True)
    body = json.loads(sent[0].content)
    assert "fallbacks" not in body and "anthropic-beta" not in sent[0].headers


def test_anthropic_refusal():
    http, _ = mock(anthropic_message("refusal"), httpx2)
    with pytest.raises(ProviderRefusal, match="no"):
        AnthropicProvider("k", http_client=http).chat("claude-opus-5-5", MESSAGES, json_mode=True)


@pytest.mark.parametrize("status", [429, 500, 529])
def test_anthropic_retryable_errors(status):
    body = {"type": "error", "error": {"type": "overloaded_error", "message": "busy"}}
    http, _ = mock(lambda r: (status, body), httpx2)
    with pytest.raises(TransientProviderError):
        AnthropicProvider("k", http_client=http).chat("claude-opus-5-5", MESSAGES, json_mode=True)


@pytest.mark.parametrize("status", [400, 401])
def test_client_errors_are_not_retried(status):
    import anthropic
    import openai

    body = {"type": "error", "error": {"type": "invalid_request_error", "message": "bad"}}
    http, _ = mock(lambda r: (status, body), httpx2)
    with pytest.raises(anthropic.APIStatusError):
        AnthropicProvider("k", http_client=http).chat("claude-opus-5-5", MESSAGES, json_mode=True)
    http, _ = mock(lambda r: (status, {"error": {"message": "bad"}}))
    with pytest.raises(openai.APIStatusError):
        OpenAIProvider("k", http_client=http).chat("gpt-4.1", MESSAGES, json_mode=True)


def test_openai_compatible_rejected_json_is_returned_for_repair():
    # Groq's reply when JSON mode output doesn't parse
    body = {
        "error": {
            "message": "Failed to validate JSON.",
            "type": "invalid_request_error",
            "code": "json_validate_failed",
            "failed_generation": '{"ok": tru',
        }
    }
    http, _ = mock(lambda r: (400, body))
    resp = OpenAIProvider("k", http_client=http).chat("openai/gpt-oss-20b", MESSAGES, True)
    assert resp.text == '{"ok": tru'
    assert resp.model == "openai/gpt-oss-20b" and resp.prompt_tokens == 0
