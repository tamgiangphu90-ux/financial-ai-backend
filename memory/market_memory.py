import json
from typing import Any

from database.session import dumps, sqlite_execute


class MarketMemory:
    def remember_event(
        self,
        symbol: str,
        event_type: str,
        summary: str,
        source: str | None = None,
        confidence_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        sqlite_execute(
            """
            INSERT INTO market_memory (symbol, event_type, summary, source, confidence_score, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (symbol.upper(), event_type, summary, source, confidence_score, dumps(metadata)),
        )

    def recent_events(self, symbol: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        if symbol:
            rows = sqlite_execute(
                "SELECT * FROM market_memory WHERE symbol = ? ORDER BY id DESC LIMIT ?",
                (symbol.upper(), limit),
            )
        else:
            rows = sqlite_execute("SELECT * FROM market_memory ORDER BY id DESC LIMIT ?", (limit,))
        for row in rows:
            try:
                row["metadata"] = json.loads(row.pop("metadata_json") or "{}")
            except json.JSONDecodeError:
                row["metadata"] = {}
        return rows
