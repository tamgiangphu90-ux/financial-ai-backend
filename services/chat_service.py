import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from intelligence.chat_orchestrator import generate_intelligent_reply
from intelligence.intent_router import intent_classifier
from intelligence.response_builder import DISCLAIMER
from memory.memory_manager import MemoryManager
from utils.config import PROJECT_DIR, get_settings


logger = logging.getLogger(__name__)
SAFE_FALLBACK_REPLY = (
    "Xin l\u1ed7i, hi\u1ec7n t\u1ea1i m\u00ecnh ch\u01b0a th\u1ec3 x\u1eed l\u00fd \u0111\u1ea7y \u0111\u1ee7 y\u00eau c\u1ea7u n\u00e0y do h\u1ec7 th\u1ed1ng AI "
    "ho\u1eb7c ngu\u1ed3n d\u1eef li\u1ec7u b\u00ean ngo\u00e0i \u0111ang t\u1ea1m th\u1eddi kh\u00f4ng s\u1eb5n s\u00e0ng. B\u1ea1n c\u00f3 th\u1ec3 th\u1eed l\u1ea1i "
    "sau \u00edt ph\u00fat. Th\u00f4ng tin n\u00e0y ch\u1ec9 mang t\u00ednh tham kh\u1ea3o, kh\u00f4ng ph\u1ea3i khuy\u1ebfn ngh\u1ecb \u0111\u1ea7u t\u01b0."
)


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


def build_safe_chat_response(
    conversation_id: str = "default",
    error: str | None = "chat_pipeline_error",
    reply: str = SAFE_FALLBACK_REPLY,
    message: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_message = message or {
        "id": 0,
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": reply,
        "market_data": [],
        "created_at": None,
    }
    return {
        "reply": reply,
        "answer": reply,
        "error": error,
        "intent": "fallback",
        "market_data": [],
        "citations": [],
        "sources": [],
        "sources_used": [],
        "reasoning": None,
        "retrieval": None,
        "memory": {},
        "summary": reply[:240],
        "analysis": reply,
        "trend": "neutral",
        "risk_level": "medium",
        "confidence_score": 0,
        "source_count": 0,
        "source_status": {},
        "related_topics": [],
        "next_questions": [],
        "disclaimer": DISCLAIMER,
        "message": safe_message,
    }


async def generate_chat_reply(message: str, conversation_id: str, history: list[Any]) -> dict[str, Any]:
    try:
        save_chat_message(conversation_id, "user", message)
        intent = intent_classifier(message)
        pipeline_result = await generate_intelligent_reply(message, history)
        memory_context = MemoryManager().build_prompt_context(
            user_id=conversation_id,
            history=history,
            symbols=pipeline_result.get("symbols", []),
        )

        reply = pipeline_result.get("answer") or SAFE_FALLBACK_REPLY
        market_data = pipeline_result.get("market_data")
        if market_data is None:
            retrieval = pipeline_result.get("retrieval") or {}
            market_data = retrieval.get("bundles", [])

        assistant_message = save_chat_message(
            conversation_id,
            "assistant",
            reply,
            market_data,
        )
        citations = pipeline_result.get("citations", [])
        api_response = pipeline_result.get("api_response") or {
            "summary": reply[:240],
            "analysis": reply,
            "trend": "neutral",
            "risk_level": "medium",
            "confidence_score": 0.0,
            "source_count": len(citations),
            "sources": citations,
            "source_status": {},
            "related_topics": [],
            "next_questions": [],
            "disclaimer": DISCLAIMER,
        }
        return {
            "reply": reply,
            "answer": reply,
            "intent": intent,
            "market_data": market_data,
            "citations": citations,
            "sources_used": citations,
            "reasoning": pipeline_result.get("analysis"),
            "retrieval": pipeline_result.get("retrieval"),
            "memory": memory_context,
            **api_response,
            "error": None,
            "sources": api_response.get("sources", citations),
            "confidence_score": api_response.get("confidence_score", 0),
            "message": assistant_message,
        }
    except Exception as exc:
        logger.exception("Chat pipeline failed for conversation_id=%s", conversation_id)
        try:
            assistant_message = save_chat_message(
                conversation_id,
                "assistant",
                SAFE_FALLBACK_REPLY,
                [],
            )
        except Exception:
            logger.exception("Could not persist fallback chat message for conversation_id=%s", conversation_id)
            assistant_message = None
        return build_safe_chat_response(
            conversation_id=conversation_id,
            error="chat_pipeline_error",
            message=assistant_message,
        )
