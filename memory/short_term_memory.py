from typing import Any


class ShortTermMemory:
    def build_context(self, history: list[Any] | None, limit: int = 8) -> list[dict[str, str]]:
        items = []
        for item in (history or [])[-limit:]:
            if isinstance(item, dict):
                role = item.get("role", "user")
                content = item.get("content", "")
            else:
                role = getattr(item, "role", "user")
                content = getattr(item, "content", str(item))
            if content:
                items.append({"role": role, "content": content})
        return items
