from typing import Any

from memory.market_memory import MarketMemory


class MarketEventTracker:
    def __init__(self) -> None:
        self.memory = MarketMemory()

    def track_from_retrieval(self, retrieval: dict[str, Any]) -> None:
        for bundle in retrieval.get("bundles", []):
            symbol = bundle.get("symbol")
            if not symbol:
                continue
            verification = bundle.get("verification") or {}
            if verification.get("discrepancies"):
                self.memory.remember_event(
                    symbol=symbol,
                    event_type="source_conflict",
                    summary="Detected conflicting source values.",
                    source=verification.get("primary_source"),
                    confidence_score=verification.get("confidence"),
                    metadata=verification,
                )
