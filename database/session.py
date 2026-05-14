import json
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from database.connection import AsyncSessionLocal, engine
from database.models import Base
from utils.config import PROJECT_DIR, get_settings


def _sqlite_path() -> Path:
    path = get_settings().chat_db_path
    if not path.is_absolute():
        path = PROJECT_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


async def init_database() -> None:
    if engine is not None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return
    _init_sqlite_fallback()


async def get_session() -> AsyncIterator[Any]:
    if AsyncSessionLocal is None:
        raise RuntimeError("SQLAlchemy async dependencies are not installed.")
    async with AsyncSessionLocal() as session:
        yield session


def _init_sqlite_fallback() -> None:
    with sqlite3.connect(_sqlite_path()) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE,
                display_name TEXT,
                preferences_json TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS watchlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                market TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                conversation_id TEXT,
                message_id TEXT,
                rating REAL,
                feedback_type TEXT,
                correction TEXT,
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS market_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                event_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                source TEXT,
                confidence_score REAL,
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def sqlite_execute(query: str, params: tuple = ()) -> list[dict[str, Any]]:
    with sqlite3.connect(_sqlite_path()) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()
        connection.commit()
        return [dict(row) for row in rows]


def dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)
