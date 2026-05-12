import asyncio
from datetime import date, timedelta
from typing import Any

import requests

from utils.config import get_settings
from utils.errors import ServiceError


FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def _format_news_item(item: dict[str, Any], sentiment: dict[str, Any] | None) -> dict[str, Any]:
    published = item.get("datetime")
    published_date = None
    if published:
        from datetime import datetime, timezone

        published_date = datetime.fromtimestamp(published, tz=timezone.utc).isoformat()

    return {
        "title": item.get("headline") or "",
        "summary": item.get("summary"),
        "source": item.get("source"),
        "published_date": published_date,
        "url": item.get("url"),
        "sentiment": sentiment,
    }


async def get_company_news(symbol: str, limit: int = 20) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.finnhub_api_key:
        raise ServiceError(
            "Missing FINNHUB_API_KEY environment variable",
            status_code=500,
            code="missing_finnhub_key",
        )

    cleaned = symbol.strip().upper().lstrip("$")
    today = date.today()
    start = today - timedelta(days=settings.market_news_days)

    try:
        news_response, sentiment_response = await asyncio.gather(
            asyncio.to_thread(
                requests.get,
                f"{FINNHUB_BASE_URL}/company-news",
                params={
                    "symbol": cleaned,
                    "from": start.isoformat(),
                    "to": today.isoformat(),
                    "token": settings.finnhub_api_key,
                },
                timeout=settings.request_timeout,
            ),
            asyncio.to_thread(
                requests.get,
                f"{FINNHUB_BASE_URL}/news-sentiment",
                params={"symbol": cleaned, "token": settings.finnhub_api_key},
                timeout=settings.request_timeout,
            ),
        )
    except requests.RequestException as exc:
        raise ServiceError(f"Cannot connect to Finnhub: {exc}", code="finnhub_unavailable") from exc

    if news_response.status_code == 401:
        raise ServiceError("FINNHUB_API_KEY is invalid", status_code=500, code="invalid_finnhub_key")
    if news_response.status_code >= 400:
        raise ServiceError(
            f"Finnhub news request failed with status {news_response.status_code}",
            code="finnhub_error",
        )

    sentiment = None
    if sentiment_response.status_code < 400:
        try:
            sentiment = sentiment_response.json()
        except ValueError:
            sentiment = None

    try:
        news = news_response.json()
    except ValueError as exc:
        raise ServiceError("Finnhub returned invalid JSON", code="finnhub_invalid_json") from exc

    if not isinstance(news, list):
        return []

    return [_format_news_item(item, sentiment) for item in news[:limit]]
