from typing import Any


def apply_relevance_filter(items: list[dict[str, Any]], query: str, symbols: list[str] | None = None) -> list[dict[str, Any]]:
    tokens = {token.lower() for token in query.replace("/", " ").replace("-", " ").split() if len(token) > 2}
    symbol_set = {symbol.upper().replace(".VN", "") for symbol in symbols or []}
    if not tokens and not symbol_set:
        return items

    relevant = []
    for item in items:
        haystack = " ".join(
            str(item.get(key) or "")
            for key in ("symbol", "title", "summary", "source", "name")
        )
        lowered = haystack.lower()
        item_symbol = str(item.get("symbol") or "").upper().replace(".VN", "")
        if item_symbol in symbol_set or any(token in lowered for token in tokens):
            relevant.append(item)
    return relevant or items
