import json
import sqlite3
from pathlib import Path
from typing import Any

from utils.config import PROJECT_DIR, get_settings


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


def init_memory() -> None:
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS favorite_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default',
                symbol TEXT NOT NULL,
                market TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, symbol)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default',
                name TEXT NOT NULL,
                symbols TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default',
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                average_cost REAL,
                currency TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def add_favorite_stock(symbol: str, market: str | None = None, user_id: str = "default") -> None:
    with get_db() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO favorite_stocks (user_id, symbol, market)
            VALUES (?, ?, ?)
            """,
            (user_id, symbol.upper(), market),
        )


def list_favorite_stocks(user_id: str = "default") -> list[dict[str, Any]]:
    with get_db() as connection:
        rows = connection.execute(
            "SELECT symbol, market, created_at FROM favorite_stocks WHERE user_id = ? ORDER BY symbol",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_watchlist(name: str, symbols: list[str], user_id: str = "default") -> None:
    payload = json.dumps([symbol.upper() for symbol in symbols])
    with get_db() as connection:
        connection.execute(
            """
            INSERT INTO watchlists (user_id, name, symbols)
            VALUES (?, ?, ?)
            """,
            (user_id, name, payload),
        )

