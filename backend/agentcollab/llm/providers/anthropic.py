from .base import (
    ProviderRefusal,
    ProviderResponse,
    TransientProviderError,
    is_retryable_status,
)

# Models that accept server-side refusal fallbacks ("default" routing)
FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


def split_system(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """Anthropic takes the system prompt as a separate field."""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system") or None
    return system, [m for m in messages if m["role"] != "system"]


class AnthropicProvider:
    def __init__(
        self,
        api_key: str | None = None,
        timeout_s: float = 300.0,
        max_tokens: int = 16000,
        http_client=None,
    ):
        import anthropic

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(
            api_key=api_key, timeout=timeout_s, max_retries=0, http_client=http_client
        )
        self._max_tokens = max_tokens

    def chat(self, model: str, messages: list[dict], json_mode: bool) -> ProviderResponse:
        # json_mode is enforced by the prompt plus the client's validate-and-repair step
        system, convo = split_system(messages)
        kwargs: dict = {
            "model": model,
            "max_tokens": self._max_tokens,
            "messages": convo,
            # Cache the prompt prefix (system + repo files) so feedback rounds reuse it
            "cache_control": {"type": "ephemeral"},
        }
        if system:
            kwargs["system"] = system
        try:
            if model in FALLBACK_MODELS:
                resp = self._client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
                )
            else:
                resp = self._client.messages.create(**kwargs)
        except (self._anthropic.APITimeoutError, self._anthropic.APIConnectionError) as e:
            raise TransientProviderError(str(e)) from e
        except self._anthropic.APIStatusError as e:
            if is_retryable_status(e.status_code):
                raise TransientProviderError(str(e)) from e
            raise

        if resp.stop_reason == "refusal":
            details = getattr(resp, "stop_details", None)
            raise ProviderRefusal(getattr(details, "explanation", None) or "model declined")

        u = resp.usage
        cache_read = u.cache_read_input_tokens or 0
        cache_write = u.cache_creation_input_tokens or 0
        return ProviderResponse(
            text="".join(b.text for b in resp.content if b.type == "text"),
            prompt_tokens=u.input_tokens + cache_read + cache_write,
            cached_tokens=cache_read,
            cache_write_tokens=cache_write,
            completion_tokens=u.output_tokens,
            model=resp.model,
        )
