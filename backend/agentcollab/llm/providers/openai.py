from .base import ProviderResponse, TransientProviderError


class OpenAIProvider:
    """OpenAI, or any OpenAI-compatible API (OpenRouter, Groq, Together, Ollama...) via base_url."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout_s: float = 90.0):
        import openai

        self._openai = openai
        self._client = openai.OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout_s, max_retries=0
        )

    def chat(self, model: str, messages: list[dict], json_mode: bool) -> ProviderResponse:
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        try:
            resp = self._client.chat.completions.create(model=model, messages=messages, **kwargs)
        except (
            self._openai.RateLimitError,
            self._openai.APITimeoutError,
            self._openai.APIConnectionError,
            self._openai.InternalServerError,
        ) as e:
            raise TransientProviderError(str(e)) from e

        usage = resp.usage
        details = getattr(usage, "prompt_tokens_details", None)
        return ProviderResponse(
            text=resp.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens,
            cached_tokens=(getattr(details, "cached_tokens", 0) or 0) if details else 0,
            completion_tokens=usage.completion_tokens,
            model=resp.model,
        )
