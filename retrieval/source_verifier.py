from datetime import datetime, timezone
from statistics import median
from typing import Any


SOURCE_WEIGHTS = {
    "FireAnt": 0.95,
    "Yahoo Finance": 0.9,
    "Finnhub": 0.85,
    "CafeF": 0.8,
}


def _as_float(value: Any) -> float | None:
    if value in (None, "", "N/A"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _source_name(item: dict[str, Any]) -> str:
    return item.get("source") or item.get("provider") or "Unknown"


def _is_stale(item: dict[str, Any], max_age_hours: int = 24) -> bool:
    raw = item.get("market_time") or item.get("published_date")
    if not raw:
        return False
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - parsed).total_seconds() > max_age_hours * 3600


def verify_price_sources(quotes: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for item in quotes:
        price = _as_float(item.get("current_price") or item.get("price"))
        if price is None:
            continue
        source = _source_name(item)
        candidates.append(
            {
                "source": source,
                "price": price,
                "currency": item.get("currency"),
                "market_time": item.get("market_time"),
                "weight": SOURCE_WEIGHTS.get(source, 0.6),
            }
        )

    if not candidates:
        return {
            "confidence": 0.0,
            "primary_price": None,
            "discrepancies": ["No comparable realtime price was available."],
            "compared_sources": [],
        }

    weighted = sorted(candidates, key=lambda item: item["weight"], reverse=True)
    primary = weighted[0]
    prices = [item["price"] for item in candidates]
    baseline = median(prices)
    discrepancies = []

    for item in candidates:
        if baseline and abs(item["price"] - baseline) / baseline > 0.02:
            discrepancies.append(
                f"{item['source']} price {item['price']} differs from median {baseline:.2f} by more than 2%."
            )

    spread = (max(prices) - min(prices)) / baseline if baseline else 0
    confidence = max(0.35, min(0.98, primary["weight"] - spread))
    if len(candidates) == 1:
        confidence = min(confidence, 0.72)
        discrepancies.append("Only one price source was available, so confidence is capped.")

    stale_sources = []
    for original in quotes:
        price = _as_float(original.get("current_price") or original.get("price"))
        if price is not None and _is_stale(original):
            stale_sources.append(_source_name(original))
    if stale_sources:
        confidence = min(confidence, 0.65)
        discrepancies.append(f"Stale data warning for: {', '.join(stale_sources)}.")

    return {
        "confidence": round(confidence, 2),
        "primary_price": primary["price"],
        "primary_source": primary["source"],
        "discrepancies": discrepancies,
        "warnings": discrepancies,
        "compared_sources": candidates,
    }


def verify_retrieval_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    quotes = bundle.get("quotes", [])
    verification = verify_price_sources(quotes)
    bundle["verification"] = verification
    return bundle
