from statistics import median
from typing import Any


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def detect_conflicts(items: list[dict[str, Any]], tolerance: float = 0.02) -> list[dict[str, Any]]:
    prices = [_number(item.get("current_price") or item.get("price")) for item in items]
    prices = [price for price in prices if price is not None]
    if len(prices) < 2:
        return []

    baseline = median(prices)
    if not baseline:
        return []

    conflicts = []
    for item in items:
        price = _number(item.get("current_price") or item.get("price"))
        if price is None:
            continue
        difference = abs(price - baseline) / baseline
        if difference > tolerance:
            conflicts.append(
                {
                    "source": item.get("source"),
                    "value": price,
                    "baseline": baseline,
                    "difference_percent": round(difference * 100, 2),
                    "warning": "Source value differs materially from the cross-source median.",
                }
            )
    return conflicts
