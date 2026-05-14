from typing import Any

from memory.long_term_memory import LongTermMemory
from memory.market_memory import MarketMemory
from memory.short_term_memory import ShortTermMemory
from memory.user_profile_memory import UserProfileMemory


class MemoryManager:
    def __init__(self) -> None:
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.user_profile = UserProfileMemory()
        self.market_memory = MarketMemory()

    def build_prompt_context(
        self,
        user_id: str | None = None,
        history: list[Any] | None = None,
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        user_id = user_id or "anonymous"
        market_events = []
        for symbol in symbols or []:
            market_events.extend(self.market_memory.recent_events(symbol, limit=5))
        return {
            "short_term": self.short_term.build_context(history),
            "user_profile": self.user_profile.profile(user_id),
            "preferences": self.long_term.get_user_preferences(user_id),
            "market_events": market_events[:10],
        }
