from typing import Any


def _key(item: dict[str, Any]) -> tuple:
    title = " ".join(str(item.get("title") or item.get("summary") or item.get("symbol") or "").lower().split())
    url = str(item.get("url") or "").lower()
    source = str(item.get("source") or "").lower()
    price = item.get("current_price") or item.get("price")
    return (title[:120], url, source, price)


def remove_duplicates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for item in items:
        key = _key(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
