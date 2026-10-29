"""Model providers. Switch with AGENTCOLLAB_PROVIDER; nothing outside this package imports a vendor SDK."""

from .base import ChatProvider, ProviderRefusal, ProviderResponse, TransientProviderError

PROVIDERS = ("openai", "anthropic", "openai_compatible")


def make_provider(name: str, api_key: str | None, base_url: str | None = None) -> ChatProvider:
    if name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(api_key)
    if name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(api_key)
    if name == "openai_compatible":
        if not base_url:
            raise ValueError("openai_compatible needs AGENTCOLLAB_BASE_URL")
        from .openai import OpenAIProvider

        return OpenAIProvider(api_key, base_url=base_url)
    raise ValueError(f"unknown provider {name!r}; choose one of {', '.join(PROVIDERS)}")


__all__ = [
    "PROVIDERS",
    "ChatProvider",
    "ProviderRefusal",
    "ProviderResponse",
    "TransientProviderError",
    "make_provider",
]
