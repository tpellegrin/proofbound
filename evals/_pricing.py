#!/usr/bin/env python3
"""What a run cost, derived from what it consumed — never stored in its place.

Token usage is what a run actually did; a dollar figure is an interpretation of it under a price
list that changes. So this module keeps the two apart: usage is recorded by `_profile`, and cost is
computed here from usage plus an explicitly identified price table. A later price change can
therefore produce a new interpretation of a historical run without altering what that run consumed,
which is the historical-semantics discipline (`P3`) applied to money.

**Price identity is part of the evidence.** Every table carries its source, the date it was read and
the schedule it applies under. A cost figure without one is an assertion.

**Peak windows are real money.** DeepSeek currently charges double during two daily windows on
weekdays, so a series that straddles a boundary cannot be costed at one rate. Each call is classified
by its own timestamp.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Read from https://api-docs.deepseek.com/quick_start/pricing on 2026-09-09.
# Prices are US dollars per 1,000,000 tokens. Verify before relying on a cost figure: this is a
# snapshot of a page that changes, not an agreement.
DEEPSEEK_2026_09_09 = {
    "id": "deepseek-2026-09-09",
    "source": "https://api-docs.deepseek.com/quick_start/pricing",
    "retrieved": "2026-09-09",
    "currency": "USD",
    "per_tokens": 1_000_000,
    "peak_windows_utc": ((1, 4), (6, 10)),
    "peak_weekdays_only": True,
    "models": {
        "deepseek-v4-flash": {
            "off_peak": {"cache_hit": 0.007, "cache_miss": 0.22, "output": 0.66},
            "peak": {"cache_hit": 0.014, "cache_miss": 0.44, "output": 1.32},
        },
        "deepseek-v4-pro": {
            "off_peak": {"cache_hit": 0.022, "cache_miss": 0.66, "output": 1.98},
            "peak": {"cache_hit": 0.044, "cache_miss": 1.32, "output": 3.96},
        },
    },
}

PEAK = "peak"
OFF_PEAK = "off-peak"
UNKNOWN = None


def price_class(when: datetime, table: dict[str, Any] = DEEPSEEK_2026_09_09) -> str:
    """Which price window one moment falls in, by its own UTC timestamp.

    A run that begins off-peak and ends inside a peak window is not one price, and classifying the
    whole series by when it started would quietly understate it.
    """
    moment = when.astimezone(timezone.utc)
    if table.get("peak_weekdays_only") and moment.weekday() >= 5:
        return OFF_PEAK
    hour = moment.hour + moment.minute / 60.0
    for start, end in table["peak_windows_utc"]:
        if start <= hour < end:
            return PEAK
    return OFF_PEAK


def cost(usage: dict[str, Any], *, model: str, when: datetime | None = None,
         window: str | None = None, table: dict[str, Any] = DEEPSEEK_2026_09_09) -> dict[str, Any]:
    """Derive a dollar figure from raw usage, and say exactly how it was derived.

    Returns `None` for the amount rather than zero when the model is not in the table or the usage
    fields needed are absent. A free model and an unpriced one are different facts, and reporting the
    second as `$0.00` would make an unknown look like a measurement.

    The cache accounting is documented inline and was measured against the provider, not assumed.
    """
    rates = (table.get("models") or {}).get(model)
    if rates is None:
        return {"amount": None, "reason": f"no price for {model!r} in {table['id']}",
                "price_id": table["id"], "window": window, "model": model}
    moment = when or datetime.now(timezone.utc)
    window = window or price_class(moment, table)
    band = rates[PEAK if window == PEAK else "off_peak"]

    total_input = usage.get("input")
    cache_read = usage.get("cache_read") or 0
    output = usage.get("output")
    if not isinstance(total_input, (int, float)) or not isinstance(output, (int, float)):
        return {"amount": None, "reason": "usage is missing input or output tokens",
                "price_id": table["id"], "window": window, "model": model}

    # **The cache accounting, measured rather than assumed.** A bounded smoke probe against
    # DeepSeek V4 Flash returned `total = 7380` with `input = 5714`, `output = 2` and
    # `cache.read = 1664` — and 5714 + 2 + 1664 is exactly 7380. So the reported input count
    # **excludes** cached tokens on this provider, and the two are additive: the input count is
    # billed at the cache-miss rate and the cache count at the cache-hit rate, on top. This is a
    # provider-specific finding, not a general one; another provider may report the input count
    # inclusive, and this arithmetic would then overstate rather than match.
    uncached = float(total_input)
    scale = table["per_tokens"]
    amount = (uncached * band["cache_miss"] + float(cache_read) * band["cache_hit"]
              + float(output) * band["output"]) / scale
    return {
        "amount": round(amount, 6),
        "currency": table["currency"],
        "price_id": table["id"],
        "source": table["source"],
        "retrieved": table["retrieved"],
        "window": window,
        "model": model,
        "basis": "input billed as cache-miss, cache_read billed on top as cache-hit "
                 "(measured: provider reports input excluding cache)",
        "billed": {"uncached_input": uncached, "cache_read": float(cache_read),
                   "output": float(output)},
        "rates": dict(band),
    }


def forecast(samples: list[dict[str, Any]], *, model: str, window: str,
             table: dict[str, Any] = DEEPSEEK_2026_09_09) -> dict[str, Any]:
    """What a planned series would cost if its runs resembled these.

    Two numbers, because one would be a guess wearing a decimal point: the median sample and the
    largest. A budget set on the median is a budget that is exceeded half the time.
    """
    amounts = []
    for usage in samples:
        got = cost(usage, model=model, window=window, table=table)
        if got["amount"] is not None:
            amounts.append(got["amount"])
    if not amounts:
        return {"per_run_median": None, "per_run_max": None, "window": window,
                "price_id": table["id"]}
    amounts.sort()
    mid = amounts[len(amounts) // 2] if len(amounts) % 2 else (
        (amounts[len(amounts) // 2 - 1] + amounts[len(amounts) // 2]) / 2)
    return {"per_run_median": round(mid, 6), "per_run_max": round(amounts[-1], 6),
            "runs_observed": len(amounts), "window": window, "price_id": table["id"],
            "source": table["source"], "retrieved": table["retrieved"]}
