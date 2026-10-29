"""Per-model prices in USD per 1M tokens.

Prices change. Check the provider's pricing page before trusting the cost numbers, and add
any model you switch to. Unknown models are logged with cost_usd = None.
- OpenAI: https://openai.com/api/pricing
- Anthropic: https://platform.claude.com/docs/en/about-claude/pricing
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    input: float
    cached_input: float
    output: float
    cache_write: float | None = None  # None means cache writes cost the same as input


PRICES: dict[str, ModelPrice] = {
    # OpenAI (caching is automatic; no write surcharge)
    "gpt-4.1": ModelPrice(input=2.00, cached_input=0.50, output=8.00),
    "gpt-4.1-mini": ModelPrice(input=0.40, cached_input=0.10, output=1.60),
    "gpt-4.1-nano": ModelPrice(input=0.10, cached_input=0.025, output=0.40),
    "gpt-4o-mini": ModelPrice(input=0.15, cached_input=0.075, output=0.60),
    "gpt-5": ModelPrice(input=1.25, cached_input=0.125, output=10.00),
    "gpt-5-mini": ModelPrice(input=0.25, cached_input=0.025, output=2.00),
    # Anthropic (5-minute cache writes cost 1.25x input)
    "claude-opus-5-5": ModelPrice(input=4.00, cached_input=0.20, output=20.00, cache_write=5.00),
    "claude-sonnet-5-5": ModelPrice(input=2.00, cached_input=0.20, output=10.00, cache_write=2.50),
    "claude-haiku-5-5": ModelPrice(input=0.10, cached_input=0.01, output=0.50, cache_write=0.125),
}


def price_for(model: str) -> ModelPrice | None:
    """Exact match, else the longest known prefix.

    APIs report dated names like gpt-4.1-2025-04-14.
    """
    if model in PRICES:
        return PRICES[model]
    matches = [name for name in PRICES if model.startswith(name + "-")]
    return PRICES[max(matches, key=len)] if matches else None


def cost_usd(
    model: str,
    prompt_tokens: int,
    cached_tokens: int,
    completion_tokens: int,
    cache_write_tokens: int = 0,
) -> float | None:
    """Cost of one call. prompt_tokens includes cached and cache-write tokens."""
    price = price_for(model)
    if price is None:
        return None
    write_rate = price.cache_write if price.cache_write is not None else price.input
    uncached = prompt_tokens - cached_tokens - cache_write_tokens
    return (
        uncached * price.input
        + cached_tokens * price.cached_input
        + cache_write_tokens * write_rate
        + completion_tokens * price.output
    ) / 1_000_000
