from datetime import datetime, timezone
from typing import Any


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def apply_freshness_filter(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    enriched = []
    for item in items:
        published = _parse_date(item.get("published_date") or item.get("market_time") or item.get("created_at"))
        age_hours = None
        if published:
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            age_hours = max(0.0, (now - published).total_seconds() / 3600)
        enriched.append({**item, "age_hours": age_hours})
    return sorted(enriched, key=lambda item: item.get("age_hours") if item.get("age_hours") is not None else 10**9)
