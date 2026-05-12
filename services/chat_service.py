import json
import sqlite3
from pathlib import Path
from typing import Any

from rag.pipeline import FinancialRAGPipeline
from utils.config import PROJECT_DIR, get_settings
from utils.errors import ServiceError


def _db_path() -> Path:
    path = get_settings().chat_db_path
    if not path.is_absolute():
        path = PROJECT_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_db():
    connection = sqlite3.connect(_db_path())
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL DEFAULT 'default',
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                market_data TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation
            ON chat_messages (conversation_id, id)
            """
        )


def serialize_message(row: sqlite3.Row) -> dict[str, Any]:
    market_data = []
    if row["market_data"]:
        try:
            market_data = json.loads(row["market_data"])
        except json.JSONDecodeError:
            market_data = []
    return {
        "id": row["id"],
        "conversation_id": row["conversation_id"],
        "role": row["role"],
        "content": row["content"],
        "market_data": market_data,
        "created_at": row["created_at"],
    }


def list_chat_messages(conversation_id: str, limit: int = 100) -> list[dict[str, Any]]:
    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT id, conversation_id, role, content, market_data, created_at
            FROM chat_messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (conversation_id, limit),
        ).fetchall()
    return [serialize_message(row) for row in reversed(rows)]


def save_chat_message(
    conversation_id: str,
    role: str,
    content: str,
    market_data: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with get_db() as connection:
        cursor = connection.execute(
            """
            INSERT INTO chat_messages (conversation_id, role, content, market_data)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, content, json.dumps(market_data or [], ensure_ascii=False)),
        )
        row = connection.execute(
            """
            SELECT id, conversation_id, role, content, market_data, created_at
            FROM chat_messages
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return serialize_message(row)


def clear_chat_messages(conversation_id: str) -> None:
    with get_db() as connection:
        connection.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (conversation_id,))


async def generate_chat_reply(message: str, conversation_id: str, history: list[Any]) -> dict[str, Any]:
    save_chat_message(conversation_id, "user", message)
    pipeline_result = await FinancialRAGPipeline().run(message, use_llm=bool(get_settings().hf_token))
    reply = pipeline_result["answer"]
    assistant_message = save_chat_message(
        conversation_id,
        "assistant",
        reply,
        pipeline_result.get("retrieval", {}).get("bundles", []),
    )
    return {
        "reply": reply,
        "answer": reply,
        "citations": pipeline_result.get("citations", []),
        "sources_used": pipeline_result.get("citations", []),
        "analysis": pipeline_result.get("analysis"),
        "retrieval": pipeline_result.get("retrieval"),
        "message": assistant_message,
    }
