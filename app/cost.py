"""Cost calculator based on usage and pricing."""

from .provider.base import Usage


def compute_cost(usage: Usage, pricing: dict) -> float | None:
    """Compute cost in USD from usage and pricing."""
    if not usage or not pricing:
        return None

    input_cost = (usage.prompt_tokens / 1_000_000) * pricing.get("input_per_1m", 0)
    output_cost = (usage.completion_tokens / 1_000_000) * pricing.get("output_per_1m", 0)

    return input_cost + output_cost
