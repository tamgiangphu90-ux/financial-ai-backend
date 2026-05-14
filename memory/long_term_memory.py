import json
from typing import Any

from database.session import sqlite_execute


class LongTermMemory:
    def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        rows = sqlite_execute("SELECT preferences_json FROM users WHERE external_id = ?", (user_id,))
        if not rows:
            return {}
        try:
            return json.loads(rows[0].get("preferences_json") or "{}")
        except json.JSONDecodeError:
            return {}

    def upsert_user_preferences(self, user_id: str, preferences: dict[str, Any]) -> None:
        sqlite_execute(
            """
            INSERT INTO users (external_id, preferences_json)
            VALUES (?, ?)
            ON CONFLICT(external_id) DO UPDATE SET preferences_json = excluded.preferences_json
            """,
            (user_id, json.dumps(preferences, ensure_ascii=False)),
        )
