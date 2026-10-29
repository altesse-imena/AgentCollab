from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProviderResponse:
    text: str
    prompt_tokens: int  # all input tokens, including cached ones
    cached_tokens: int  # input tokens read from the provider's prompt cache
    completion_tokens: int
    cache_write_tokens: int = 0  # input tokens written to the cache (Anthropic bills these higher)
    model: str | None = None  # model that actually served the call, if the provider reports it


class TransientProviderError(Exception):
    """A failure worth retrying: rate limits, timeouts, 5xx errors."""


def is_retryable_status(status: int | None) -> bool:
    """429 and every 5xx (including Anthropic's 529 "overloaded") are worth retrying."""
    return status is not None and (status == 429 or status >= 500)


class ProviderRefusal(Exception):
    """The model declined the request. Retrying the same request won't help."""


class ChatProvider(Protocol):
    """Every provider takes OpenAI-style messages: a list of {"role", "content"} dicts,
    with an optional leading system message. Adapters convert to their own format."""

    def chat(self, model: str, messages: list[dict], json_mode: bool) -> ProviderResponse: ...
