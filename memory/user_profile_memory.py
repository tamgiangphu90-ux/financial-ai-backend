from typing import Any

from database.session import sqlite_execute


class UserProfileMemory:
    def profile(self, user_id: str) -> dict[str, Any]:
        rows = sqlite_execute("SELECT external_id, display_name, preferences_json, created_at FROM users WHERE external_id = ?", (user_id,))
        return rows[0] if rows else {"external_id": user_id, "preferences_json": "{}", "created_at": None}
