from typing import Any

from retrieval.source_registry import reliability_for


def rank_sources(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def score(item: dict[str, Any]) -> float:
        reliability = reliability_for(item.get("source"))
        freshness_bonus = 0.05 if item.get("age_hours") is not None and item["age_hours"] <= 24 else 0
        penalty = 0.15 if item.get("error") else 0
        return reliability + freshness_bonus - penalty

    return sorted(({**item, "rank_score": round(score(item), 3)} for item in results), key=lambda item: item["rank_score"], reverse=True)
