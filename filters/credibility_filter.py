from typing import Any

from retrieval.source_registry import reliability_for


def apply_credibility_filter(items: list[dict[str, Any]], minimum_score: float = 0.55) -> list[dict[str, Any]]:
    filtered = []
    for item in items:
        score = reliability_for(item.get("source"))
        if score >= minimum_score:
            filtered.append({**item, "reliability_score": score})
    return sorted(filtered, key=lambda item: item.get("reliability_score", 0), reverse=True)
