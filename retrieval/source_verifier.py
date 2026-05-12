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

    return {
        "confidence": round(confidence, 2),
        "primary_price": primary["price"],
        "primary_source": primary["source"],
        "discrepancies": discrepancies,
        "compared_sources": candidates,
    }


def verify_retrieval_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    quotes = bundle.get("quotes", [])
    verification = verify_price_sources(quotes)
    bundle["verification"] = verification
    return bundle

