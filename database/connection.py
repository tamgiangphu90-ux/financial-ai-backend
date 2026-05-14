from pathlib import Path
from typing import Any

from utils.config import PROJECT_DIR, get_settings

try:
    from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
except ModuleNotFoundError:  # Allows the app to explain missing deps instead of crashing during import.
    AsyncEngine = None
    async_sessionmaker = None
    create_async_engine = None


def database_url() -> str:
    raw = getattr(get_settings(), "database_url", None)
    if raw:
        if raw.startswith("postgres://"):
            return raw.replace("postgres://", "postgresql+asyncpg://", 1)
        if raw.startswith("postgresql://") and "+asyncpg" not in raw:
            return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
        return raw

    sqlite_path = get_settings().chat_db_path
    if not sqlite_path.is_absolute():
        sqlite_path = PROJECT_DIR / sqlite_path
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{sqlite_path.as_posix()}"


engine: Any = create_async_engine(database_url(), future=True) if create_async_engine else None
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False) if async_sessionmaker and engine else None
