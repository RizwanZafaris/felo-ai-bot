"""Token rates and per-call cost calculations (USD per 1M tokens)."""

COST_RATES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30},
    "claude-haiku-4-5":  {"input": 0.80, "output":  4.00, "cache_write": 1.00, "cache_read": 0.08},
    "claude-opus-4-7":   {"input": 15.00, "output": 75.00, "cache_write": 0.0, "cache_read": 0.0},
    "gpt-4o":            {"input": 2.50, "output": 10.00, "cache_write": 0.0, "cache_read": 0.0},
    "gpt-4o-mini":       {"input": 0.15, "output":  0.60, "cache_write": 0.0, "cache_read": 0.0},
    "gemini-1.5-pro":    {"input": 1.25, "output":  5.00, "cache_write": 0.0, "cache_read": 0.0},
    "deepseek-chat":     {"input": 0.27, "output":  1.10, "cache_write": 0.0, "cache_read": 0.0},
}


def calculate_cost(
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_write_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    rates = COST_RATES.get(model)
    if not rates:
        return 0.0
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + cache_write_tokens * rates["cache_write"]
        + cache_read_tokens * rates["cache_read"]
    ) / 1_000_000
