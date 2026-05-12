import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import requests

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    BeautifulSoup = None

from utils.config import get_settings
from utils.errors import ServiceError


CAFEF_BASE_URL = "https://s.cafef.vn"


def normalize_cafef_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper().lstrip("$").split(".", 1)[0]
    if not cleaned or not cleaned.isalnum():
        raise ServiceError("Invalid CafeF symbol", status_code=400, code="invalid_cafef_symbol")
    return cleaned


def _number_from_text(value: str | None) -> float | int | None:
    if not value:
        return None
    text = value.replace(",", "").replace("%", "").strip()
    text = re.sub(r"[^\d.\-]", "", text)
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def _extract_value(label: str, text: str) -> float | int | None:
    pattern = rf"{re.escape(label)}\s*[:\-]?\s*([\-+]?\d[\d.,]*)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return _number_from_text(match.group(1)) if match else None


def _scrape_cafef_stock_sync(symbol: str) -> dict[str, Any]:
    settings = get_settings()
    normalized = normalize_cafef_symbol(symbol)
    url = f"{CAFEF_BASE_URL}/hose/{normalized}.chn"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        response = requests.get(url, headers=headers, timeout=settings.request_timeout)
    except requests.RequestException as exc:
        raise ServiceError(f"Cannot connect to CafeF: {exc}", code="cafef_unavailable") from exc

    if response.status_code in {401, 403, 429}:
        raise ServiceError(
            f"CafeF blocked request with status {response.status_code}",
            status_code=502,
            code="cafef_blocked",
        )
    if response.status_code >= 400:
        raise ServiceError(
            f"CafeF request failed with status {response.status_code}",
            status_code=502,
            code="cafef_error",
        )
    if BeautifulSoup is None:
        raise ServiceError(
            "beautifulsoup4 is not installed for CafeF scraping",
            status_code=500,
            code="missing_bs4",
        )

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(" ", strip=True)
    if "captcha" in text.lower() or "access denied" in text.lower():
        raise ServiceError("CafeF blocked scraping", status_code=502, code="cafef_blocked")

    title = soup.title.string.strip() if soup.title and soup.title.string else normalized
    current_price = _extract_value("Giá hiện tại", text) or _extract_value("Giá", text)
    change_percent = _extract_value("%", text)
    volume = _extract_value("Khối lượng", text) or _extract_value("KLGD", text)
    market_cap = _extract_value("Vốn hóa", text)

    return {
        "symbol": normalized,
        "name": title,
        "current_price": current_price,
        "change_percent": change_percent,
        "volume": volume,
        "market_cap": market_cap,
        "currency": "VND",
        "market_time": datetime.now(timezone.utc).isoformat(),
        "source": "CafeF",
        "url": url,
        "raw_excerpt": text[:500],
        "warnings": [] if any((current_price, volume, market_cap)) else ["CafeF page parsed but quote fields were limited"],
    }


async def get_cafef_stock_data(symbol: str) -> dict[str, Any]:
    return await asyncio.to_thread(_scrape_cafef_stock_sync, symbol)

