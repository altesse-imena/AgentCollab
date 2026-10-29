import re
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

    def __init__(self, message: str = "", retry_after_s: float | None = None):
        super().__init__(message)
        self.retry_after_s = retry_after_s  # how long the provider asked us to wait, if it said


_TRY_AGAIN = re.compile(r"try again in (?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", re.IGNORECASE)


def retry_after_s(error) -> float | None:
    """Seconds the provider asked us to wait: the Retry-After header, or failing that a
    "try again in 6m8s" hint in the message (Groq's wording). Date values are ignored."""
    headers = getattr(getattr(error, "response", None), "headers", None) or {}
    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        pass
    match = _TRY_AGAIN.search(str(error))
    if not match or not any(match.groups()):
        return None
    hours, minutes, seconds = (float(g or 0) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def is_retryable_status(status: int | None) -> bool:
    """429 and every 5xx (including Anthropic's 529 "overloaded") are worth retrying."""
    return status is not None and (status == 429 or status >= 500)


class ProviderRefusal(Exception):
    """The model declined the request. Retrying the same request won't help."""


class ChatProvider(Protocol):
    """Every provider takes OpenAI-style messages: a list of {"role", "content"} dicts,
    with an optional leading system message. Adapters convert to their own format."""

    def chat(self, model: str, messages: list[dict], json_mode: bool) -> ProviderResponse: ...
