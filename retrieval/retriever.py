import asyncio
import re
from typing import Any

from services.cafef_service import get_cafef_stock_data
from services.finnhub_service import get_company_news
from services.fireant_service import FireAntError, get_vietnam_stock_data
from services.yahoo_service import get_market_summary, get_stock_quote, get_top_movers
from utils.errors import ServiceError


VIETNAMESE_HINTS = (
    "vn-index",
    "vnindex",
    "hose",
    "hnx",
    "upcom",
    "viet nam",
    "việt nam",
    "cổ phiếu",
    "chứng khoán",
)
IGNORED_SYMBOLS = {
    "AI",
    "API",
    "GDP",
    "USD",
    "VND",
    "ETF",
    "CEO",
    "CFO",
    "EPS",
    "PE",
    "ROE",
    "ROI",
    "RAG",
    "HOM",
    "NAY",
    "THE",
    "NAO",
    "THI",
    "TRUONG",
    "CO",
    "PHIEU",
    "HOMNAY",
}
ALIASES = {
    "VNINDEX": "VNINDEX",
    "VN-INDEX": "VNINDEX",
    "VN30": "VN30",
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW": "^DJI",
}


def detect_language(text: str) -> str:
    lower = text.lower()
    vietnamese_chars = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    if any(char in lower for char in vietnamese_chars):
        return "vi"
    if any(hint in lower for hint in VIETNAMESE_HINTS):
        return "vi"
    return "en"


def detect_symbols(text: str) -> list[str]:
    symbols = set()
    upper = text.upper()

    for alias, mapped in ALIASES.items():
        if alias in upper:
            symbols.add(mapped)

    for match in re.findall(r"\$?[A-Za-z][A-Za-z0-9.-]{1,12}", text):
        is_cash_tag = match.startswith("$")
        cleaned = match.lstrip("$").rstrip(".")
        if not is_cash_tag and cleaned != cleaned.upper():
            continue

        cleaned = cleaned.upper()
        if cleaned not in IGNORED_SYMBOLS:
            symbols.add(ALIASES.get(cleaned, cleaned))

    return list(symbols)[:8]


def is_vietnam_market(symbol: str, text: str = "") -> bool:
    cleaned = symbol.upper().replace(".VN", "")
    lower = text.lower()
    if cleaned in {"VNINDEX", "VN30", "HNX", "UPCOM"}:
        return True
    if any(hint in lower for hint in VIETNAMESE_HINTS):
        return bool(re.fullmatch(r"[A-Z]{3}", cleaned))
    return bool(re.fullmatch(r"[A-Z]{3}\.VN", symbol.upper()))


async def _safe(label: str, coro):
    try:
        return await coro
    except (ServiceError, FireAntError, ValueError) as exc:
        return {"source": label, "error": str(exc)}


async def _safe_thread(label: str, func, *args):
    try:
        return await asyncio.to_thread(func, *args)
    except (ServiceError, FireAntError, ValueError) as exc:
        return {"source": label, "error": str(exc)}


class RetrievalEngine:
    async def retrieve_for_symbol(self, symbol: str, user_text: str = "") -> dict[str, Any]:
        cleaned = symbol.strip().upper().lstrip("$")
        vietnam = is_vietnam_market(cleaned, user_text)
        tasks = []
        vn_base_symbol = cleaned.replace(".VN", "")

        if not vietnam:
            tasks.append(_safe("Yahoo Finance", get_stock_quote(cleaned)))
        elif vn_base_symbol not in {"VNINDEX", "VN30", "HNX", "UPCOM"}:
            tasks.append(_safe("Yahoo Finance", get_stock_quote(f"{vn_base_symbol}.VN")))

        tasks.append(_safe("Finnhub", get_company_news(vn_base_symbol)))

        if vietnam:
            tasks.extend(
                [
                    _safe_thread("FireAnt", get_vietnam_stock_data, vn_base_symbol),
                    _safe("CafeF", get_cafef_stock_data(vn_base_symbol)),
                ]
            )

        results = await asyncio.gather(*tasks)
        quotes = []
        news = []
        errors = []
        for result in results:
            if isinstance(result, dict) and result.get("error"):
                errors.append(result)
            elif isinstance(result, list):
                news.extend(result)
            elif isinstance(result, dict):
                quotes.append(result)

        return {
            "symbol": cleaned,
            "market": "vietnam" if vietnam else "global",
            "quotes": quotes,
            "news": news,
            "errors": errors,
        }

    async def retrieve(self, message: str, symbol: str | None = None) -> dict[str, Any]:
        symbols = [symbol.strip().upper()] if symbol else detect_symbols(message)
        language = detect_language(message)
        intent = self.detect_intent(message)

        if not symbols and intent in {"market_summary", "top_movers"}:
            summary_task = get_market_summary()
            movers_task = get_top_movers()
            summary, movers = await asyncio.gather(summary_task, movers_task, return_exceptions=True)
            return {
                "language": language,
                "intent": intent,
                "symbols": [],
                "market_summary": summary if isinstance(summary, dict) else None,
                "top_movers": movers if isinstance(movers, dict) else None,
                "bundles": [],
            }

        bundles = await asyncio.gather(
            *(self.retrieve_for_symbol(item, message) for item in symbols[:4]),
            return_exceptions=False,
        )
        return {
            "language": language,
            "intent": intent,
            "symbols": symbols,
            "bundles": bundles,
        }

    def detect_intent(self, message: str) -> str:
        lower = message.lower()
        if any(term in lower for term in ("top mover", "tăng mạnh", "giảm mạnh", "movers")):
            return "top_movers"
        if any(term in lower for term in ("vn-index", "vnindex", "market", "thị trường", "hôm nay")):
            return "market_summary"
        if any(term in lower for term in ("news", "tin tức", "tin mới")):
            return "news"
        return "analysis"
