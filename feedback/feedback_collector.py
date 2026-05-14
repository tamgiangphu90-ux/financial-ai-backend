from typing import Any

from database.session import dumps, sqlite_execute


class FeedbackCollector:
    def collect(self, payload: dict[str, Any]) -> dict[str, Any]:
        sqlite_execute(
            """
            INSERT INTO feedback (user_id, conversation_id, message_id, rating, feedback_type, correction, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("user_id"),
                payload.get("conversation_id"),
                payload.get("message_id"),
                payload.get("rating"),
                payload.get("feedback_type"),
                payload.get("correction"),
                dumps(payload.get("metadata")),
            ),
        )
        return {"status": "ok", "stored": True}
