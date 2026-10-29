"""Per-model prices in USD per 1M tokens.

Prices change. Check https://openai.com/api/pricing before trusting the cost numbers,
and add any model you switch to. Unknown models are logged with cost_usd = None.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    input: float
    cached_input: float
    output: float


PRICES: dict[str, ModelPrice] = {
    "gpt-4.1": ModelPrice(input=2.00, cached_input=0.50, output=8.00),
    "gpt-4.1-mini": ModelPrice(input=0.40, cached_input=0.10, output=1.60),
    "gpt-4.1-nano": ModelPrice(input=0.10, cached_input=0.025, output=0.40),
    "gpt-4o-mini": ModelPrice(input=0.15, cached_input=0.075, output=0.60),
    "gpt-5": ModelPrice(input=1.25, cached_input=0.125, output=10.00),
    "gpt-5-mini": ModelPrice(input=0.25, cached_input=0.025, output=2.00),
}


def cost_usd(model: str, prompt_tokens: int, cached_tokens: int, completion_tokens: int) -> float | None:
    """Cost of one call. Cached tokens are part of prompt_tokens and billed at the cached rate."""
    price = PRICES.get(model)
    if price is None:
        return None
    uncached = prompt_tokens - cached_tokens
    return (
        uncached * price.input + cached_tokens * price.cached_input + completion_tokens * price.output
    ) / 1_000_000
