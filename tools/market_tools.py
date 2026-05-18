import asyncio
import logging
from typing import Any

from intelligence.intent_router import index_symbol_from_message, lower_text
from intelligence.response_formatter import market_index_answer, quote_to_market_card
from services.fireant_service import FireAntError, get_vietnam_stock_data
from services.yahoo_service import get_market_summary, get_stock_quote


logger = logging.getLogger(__name__)


async def get_market_index_context(message: str) -> dict[str, Any]:
    requested = index_symbol_from_message(message)
    if requested:
        symbols = [requested]
    else:
        symbols = ["^VNINDEX", "^DJI", "^IXIC"] if "chỉ số" in lower_text(message) else []

    quotes: list[dict[str, Any]] = []
    if symbols:
        results = await asyncio.gather(*(_fetch_index_quote(symbol) for symbol in symbols), return_exceptions=True)
        for result in results:
            if isinstance(result, dict):
                quotes.append(result)
            else:
                logger.warning("Market index quote failed: %s", result)
    else:
        try:
            summary = await get_market_summary()
        except Exception as exc:
            logger.exception("Market summary source failed: %s", exc)
            summary = {}
        quotes = [item for item in summary.get("indices", []) if isinstance(item, dict)]

    market_data = [quote_to_market_card(quote) for quote in quotes]
    answer = market_index_answer(message, quotes)
    if quotes:
        source_names = sorted({str(quote.get("source")) for quote in quotes if quote.get("source")})
        if source_names:
            answer += "\n\nNguồn: " + ", ".join(source_names)
    return {
        "answer": answer,
        "analysis": {"intent": "market_index", "mode": "market_data"},
        "retrieval": {"intent": "market_index", "symbols": symbols, "market_summary": {"indices": quotes}},
        "citations": [{"source": quote.get("source"), "symbol": quote.get("symbol")} for quote in quotes],
        "market_data": market_data,
    }


async def _fetch_index_quote(symbol: str) -> dict[str, Any]:
    try:
        return await get_stock_quote(symbol)
    except Exception as yahoo_error:
        logger.warning("Yahoo index quote failed for %s: %s", symbol, yahoo_error)

    if symbol == "^VNINDEX":
        try:
            quote = await asyncio.to_thread(get_vietnam_stock_data, "VNINDEX")
            return {**quote, "symbol": "VNINDEX", "source": quote.get("source") or "FireAnt"}
        except (FireAntError, ValueError) as fireant_error:
            logger.warning("FireAnt VNINDEX quote failed: %s", fireant_error)

    raise ValueError(f"Could not fetch index data for {symbol}")
