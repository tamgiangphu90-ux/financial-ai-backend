import os
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR.parent
logger = logging.getLogger(__name__)
ZALO_SECRET_ENV_NAMES = (
    "ZALO_APP_SECRET_KEY",
    "ZALO_APP_SECRET",
    "ZALO_SECRET_KEY",
)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_DIR / ".env")
    load_dotenv(BASE_DIR / ".env")
except ModuleNotFoundError:
    _load_env_file(PROJECT_DIR / ".env")
    _load_env_file(BASE_DIR / ".env")


def _first_available_env(names: tuple[str, ...]) -> tuple[str | None, str | None]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value, name
    return None, None


ZALO_APP_SECRET_KEY, ZALO_APP_SECRET_ENV_NAME = _first_available_env(ZALO_SECRET_ENV_NAMES)


@dataclass(frozen=True)
class Settings:
    app_name: str = "Financial AI Backend"
    environment: str = os.getenv("ENVIRONMENT", "development")
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "*")
    finnhub_api_key: str | None = os.getenv("FINNHUB_API_KEY")
    hf_token: str | None = os.getenv("HF_TOKEN")
    hf_api_url: str = os.getenv(
        "HF_API_URL",
        "https://router.huggingface.co/v1/chat/completions",
    )
    hf_model: str = os.getenv("HF_MODEL", "katanemo/Arch-Router-1.5B:hf-inference")
    fireant_token: str | None = os.getenv("FIREANT_TOKEN")
    zalo_app_secret_key: str | None = ZALO_APP_SECRET_KEY
    zalo_app_secret_env_name: str | None = ZALO_APP_SECRET_ENV_NAME
    database_url: str | None = os.getenv("DATABASE_URL")
    redis_url: str | None = os.getenv("REDIS_URL")
    chroma_persist_dir: Path = Path(os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "data" / "chroma")))
    chat_db_path: Path = Path(os.getenv("CHAT_DB_PATH", str(BASE_DIR / "chat_history.db")))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
    market_news_days: int = int(os.getenv("MARKET_NEWS_DAYS", "14"))

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.zalo_app_secret_env_name:
        logger.info("Zalo authentication secret configured from %s", settings.zalo_app_secret_env_name)
    else:
        logger.warning("Zalo authentication secret is not configured")
    return settings
