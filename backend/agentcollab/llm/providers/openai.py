from .base import ProviderResponse, TransientProviderError, is_retryable_status, retry_after_s


class OpenAIProvider:
    """OpenAI, or any OpenAI-compatible API (OpenRouter, Groq, Together, Ollama...) via base_url."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_s: float = 90.0,
        http_client=None,
    ):
        import openai

        self._openai = openai
        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_s,
            max_retries=0,
            http_client=http_client,
        )

    def chat(self, model: str, messages: list[dict], json_mode: bool) -> ProviderResponse:
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        try:
            resp = self._client.chat.completions.create(model=model, messages=messages, **kwargs)
        except (self._openai.APITimeoutError, self._openai.APIConnectionError) as e:
            raise TransientProviderError(str(e)) from e
        except self._openai.APIStatusError as e:
            if is_retryable_status(e.status_code):
                raise TransientProviderError(str(e), retry_after_s(e)) from e
            if (draft := _rejected_json(e)) is not None:
                # Usage isn't reported for rejected replies, so tokens are logged as 0.
                return ProviderResponse(
                    text=draft, prompt_tokens=0, cached_tokens=0, completion_tokens=0, model=model
                )
            raise

        usage = resp.usage
        details = getattr(usage, "prompt_tokens_details", None)
        return ProviderResponse(
            text=resp.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens,
            cached_tokens=(getattr(details, "cached_tokens", 0) or 0) if details else 0,
            completion_tokens=usage.completion_tokens,
            model=resp.model,
        )


def _rejected_json(error) -> str | None:
    """Groq rejects JSON-mode replies that don't parse with a 400 that carries the model's
    draft. Returning the draft lets the client's repair step ask for a fix instead of failing."""
    body = error.body if isinstance(error.body, dict) else {}
    body = body.get("error", body) if isinstance(body.get("error"), dict) else body
    if body.get("code") == "json_validate_failed":
        return str(body.get("failed_generation") or "")
    return None
