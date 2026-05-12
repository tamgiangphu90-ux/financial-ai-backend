import asyncio
from pathlib import Path
from typing import Any

try:
    import yfinance as yf

    if hasattr(yf, "set_tz_cache_location"):
        yf.set_tz_cache_location(str(Path(__file__).resolve().parents[1] / "data" / "yfinance_cache"))
except ModuleNotFoundError:
    yf = None

from utils.errors import ServiceError


SYMBOL_ALIASES = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "BNB": "BNB-USD",
    "SOL": "SOL-USD",
    "XRP": "XRP-USD",
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW": "^DJI",
}


def normalize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper().lstrip("$")
    if not cleaned:
        raise ServiceError("Symbol is required", status_code=400, code="invalid_symbol")
    return SYMBOL_ALIASES.get(cleaned, cleaned)


def _number(value: Any) -> float | int | None:
    if value in (None, "", "N/A"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _fetch_stock_quote_sync(symbol: str) -> dict[str, Any]:
    if yf is None:
        raise ServiceError(
            "Missing yfinance package. Install backend/requirements.txt before using market data.",
            status_code=500,
            code="missing_yfinance",
        )

    normalized = normalize_symbol(symbol)
    ticker = yf.Ticker(normalized)

    try:
        fast_info = dict(ticker.fast_info or {})
    except Exception:
        fast_info = {}

    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    current_price = _number(
        fast_info.get("last_price")
        or info.get("currentPrice")
        or info.get("regularMarketPrice")
        or info.get("previousClose")
    )
    previous_close = _number(fast_info.get("previous_close") or info.get("previousClose"))
    day_high = _number(fast_info.get("day_high") or info.get("dayHigh"))
    day_low = _number(fast_info.get("day_low") or info.get("dayLow"))
    volume = _number(fast_info.get("last_volume") or info.get("volume") or info.get("regularMarketVolume"))
    market_cap = _number(fast_info.get("market_cap") or info.get("marketCap"))
    currency = fast_info.get("currency") or info.get("currency")
    fifty_two_week_low = _number(fast_info.get("year_low") or info.get("fiftyTwoWeekLow"))
    fifty_two_week_high = _number(fast_info.get("year_high") or info.get("fiftyTwoWeekHigh"))

    if current_price is None and previous_close is None:
        raise ServiceError(
            f"Could not fetch Yahoo Finance data for {symbol}",
            status_code=404,
            code="stock_not_found",
        )

    return {
        "symbol": normalized,
        "name": info.get("longName") or info.get("shortName"),
        "current_price": current_price,
        "previous_close": previous_close,
        "day_high": day_high,
        "day_low": day_low,
        "volume": int(volume) if isinstance(volume, (int, float)) else None,
        "market_cap": market_cap,
        "currency": currency,
        "fifty_two_week_range": {
            "low": fifty_two_week_low,
            "high": fifty_two_week_high,
        },
        "exchange": info.get("exchange") or info.get("fullExchangeName"),
        "source": "Yahoo Finance",
    }


async def get_stock_quote(symbol: str) -> dict[str, Any]:
    return await asyncio.to_thread(_fetch_stock_quote_sync, symbol)


async def get_market_summary() -> dict[str, Any]:
    symbols = ["^GSPC", "^IXIC", "^DJI", "GC=F", "CL=F", "BTC-USD"]
    results = await asyncio.gather(
        *(get_stock_quote(symbol) for symbol in symbols),
        return_exceptions=True,
    )
    return {
        "indices": [
            result
            for result in results
            if isinstance(result, dict)
        ],
        "source": "Yahoo Finance",
    }


async def get_top_movers() -> dict[str, Any]:
    watchlist = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "V", "JPM"]
    quotes = await asyncio.gather(
        *(get_stock_quote(symbol) for symbol in watchlist),
        return_exceptions=True,
    )
    movers = []
    for quote in quotes:
        if not isinstance(quote, dict):
            continue
        previous = quote.get("previous_close")
        current = quote.get("current_price")
        change_percent = None
        if previous and current is not None:
            change_percent = round((current - previous) / previous * 100, 2)
        movers.append({**quote, "change_percent": change_percent})

    movers.sort(key=lambda item: abs(item.get("change_percent") or 0), reverse=True)
    return {"movers": movers[:10], "source": "Yahoo Finance"}
