import json
import asyncio
import logging
import random
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

import requests

from rag.pipeline import FinancialRAGPipeline
from retrieval.retriever import detect_symbols
from services.fireant_service import FireAntError, get_vietnam_stock_data
from services.yahoo_service import get_market_summary, get_stock_quote
from utils.config import PROJECT_DIR, get_settings

logger = logging.getLogger(__name__)

INDEX_ALIASES = {
    "VNINDEX": "^VNINDEX",
    "VN-INDEX": "^VNINDEX",
    "VN INDEX": "^VNINDEX",
    "DOW JONES": "^DJI",
    "DOW": "^DJI",
    "DJIA": "^DJI",
    "NASDAQ": "^IXIC",
    "NASDAQ COMPOSITE": "^IXIC",
}

STOCK_WORDS = (
    "cổ phiếu",
    "co phieu",
    "chứng khoán",
    "chung khoan",
    "mã",
    "ma",
    "phân tích",
    "phan tich",
    "định giá",
    "dinh gia",
    "khuyến nghị",
    "khuyen nghi",
    "mua",
    "bán",
    "ban",
    "nắm giữ",
    "nam giu",
    "stock",
    "ticker",
    "share",
)
MACRO_WORDS = (
    "vĩ mô",
    "vi mo",
    "lạm phát",
    "lam phat",
    "gdp",
    "lãi suất",
    "lai suat",
    "tỷ giá",
    "ty gia",
    "fed",
    "ngân hàng trung ương",
    "ngan hang trung uong",
    "cpi",
    "kinh tế",
    "kinh te",
    "macro",
    "inflation",
    "interest rate",
)
EDUCATION_WORDS = (
    "là gì",
    "la gi",
    "nghĩa là gì",
    "nghia la gi",
    "giải thích",
    "giai thich",
    "học",
    "hoc",
    "cách hiểu",
    "cach hieu",
    "khái niệm",
    "khai niem",
    "định nghĩa",
    "dinh nghia",
    "what is",
    "explain",
    "how does",
)
NEWS_WORDS = ("tin tức", "tin tuc", "tin mới", "tin moi", "news", "cập nhật", "cap nhat", "sự kiện", "su kien")
MARKET_WORDS = (
    "vnindex",
    "vn-index",
    "dow jones",
    "nasdaq",
    "sp500",
    "s&p 500",
    "chỉ số",
    "chi so",
    "index",
    "thị trường",
    "thi truong",
)


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return stripped.replace("\u0111", "d").replace("\u0110", "D")


def _lower_text(text: str) -> str:
    lower = " ".join(text.lower().split())
    plain = " ".join(_strip_accents(lower).split())
    return f"{lower} {plain}"


def _index_symbol_from_message(message: str) -> str | None:
    upper = re.sub(r"\s+", " ", message.upper())
    for alias, symbol in INDEX_ALIASES.items():
        if alias in upper:
            return symbol
    if "SP500" in upper or "S&P 500" in upper:
        return "^GSPC"
    return None


def intent_classifier(message: str) -> str:
    """Classify the user's financial-chat intent before data retrieval."""
    lower = _lower_text(message)
    symbols = detect_symbols(message)
    index_symbol = _index_symbol_from_message(message)

    if index_symbol or any(word in lower for word in MARKET_WORDS):
        return "market_index"
    if any(word in lower for word in NEWS_WORDS):
        return "news_query"
    if symbols and any(word in lower for word in STOCK_WORDS):
        return "stock_analysis"
    if symbols and len(symbols) <= 3:
        return "stock_analysis"
    if any(word in lower for word in MACRO_WORDS):
        return "macroeconomics"
    if any(word in lower for word in EDUCATION_WORDS):
        return "finance_education"
    if any(word in lower for word in ("tài chính", "tai chinh", "đầu tư", "dau tu", "finance", "investment", "tiết kiệm", "tiet kiem")):
        return "finance_education"
    return "general_ai_chat"


def _safe_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _quote_to_market_card(quote: dict[str, Any]) -> dict[str, Any]:
    price = _safe_number(quote.get("current_price") or quote.get("price"))
    previous = _safe_number(quote.get("previous_close"))
    change = price - previous if price is not None and previous else None
    change_percent = round(change / previous * 100, 2) if change is not None and previous else None
    return {
        "symbol": str(quote.get("symbol") or ""),
        "name": quote.get("name"),
        "price": price or 0,
        "currency": quote.get("currency"),
        "change": round(change, 2) if change is not None else None,
        "change_percent": change_percent,
        "previous_close": previous,
        "exchange": quote.get("exchange"),
        "source": quote.get("source"),
    }


def _market_index_answer(message: str, quotes: list[dict[str, Any]]) -> str:
    if not quotes:
        return (
            "Mình chưa lấy được dữ liệu chỉ số ngay lúc này. Bạn có thể thử lại sau vài phút, "
            "hoặc hỏi thêm về bối cảnh như lãi suất, dòng tiền hay nhóm ngành dẫn dắt."
        )

    lines = []
    for quote in quotes:
        card = _quote_to_market_card(quote)
        change = card.get("change_percent")
        direction = "tăng" if change and change > 0 else "giảm" if change and change < 0 else "đi ngang"
        change_text = f"{change:+.2f}%" if change is not None else "chưa có % thay đổi"
        lines.append(
            f"- {card['symbol']}: khoảng {card['price']:,g} {card.get('currency') or ''}, {direction} ({change_text})."
        )

    return (
        "Mình xem nhanh dữ liệu chỉ số cho bạn:\n"
        + "\n".join(lines)
        + "\n\nDiễn giải nhanh: hãy nhìn cùng lúc mức thay đổi, thanh khoản và tin vĩ mô trong ngày; "
        "một phiên tăng/giảm riêng lẻ chưa đủ để kết luận xu hướng trung hạn."
    )


def _news_answer_from_retrieval(message: str, retrieval: dict[str, Any]) -> str:
    items: list[dict[str, Any]] = []
    for bundle in retrieval.get("bundles", []):
        for item in bundle.get("news", [])[:5]:
            if isinstance(item, dict) and item.get("title"):
                items.append({**item, "symbol": bundle.get("symbol")})

    if not items:
        return (
            "Mình chưa tìm thấy tin mới đủ rõ cho câu hỏi này. Nếu bạn nêu mã cụ thể hơn "
            "(ví dụ FPT, VNM, AAPL), mình sẽ kiểm tra lại theo nguồn tin thị trường."
        )

    lines = []
    for item in items[:6]:
        source = item.get("source") or "nguồn tin"
        symbol = f"{item.get('symbol')}: " if item.get("symbol") else ""
        lines.append(f"- {symbol}{item.get('title')} ({source})")

    return (
        "Mình tìm được một số tin liên quan:\n"
        + "\n".join(lines)
        + "\n\nCách đọc nhanh: hãy ưu tiên tin có ảnh hưởng trực tiếp tới doanh thu, lợi nhuận, "
        "dòng tiền hoặc rủi ro pháp lý; tiêu đề tích cực chưa chắc đồng nghĩa giá sẽ tăng ngay."
    )


async def _call_llm(system_prompt: str, user_prompt: str, fallback: str, max_tokens: int = 520) -> str:
    settings = get_settings()
    if not settings.hf_token:
        return fallback

    payload = {
        "model": settings.hf_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.75,
    }
    headers = {"Authorization": f"Bearer {settings.hf_token}", "Content-Type": "application/json"}

    try:
        response = await asyncio.to_thread(
            requests.post,
            settings.hf_api_url,
            headers=headers,
            json=payload,
            timeout=60,
        )
        if response.status_code >= 400:
            logger.warning("LLM request failed with status %s: %s", response.status_code, response.text[:300])
            return fallback
        data = response.json()
        return data["choices"][0]["message"]["content"].strip() or fallback
    except Exception as exc:
        logger.exception("LLM fallback failed: %s", exc)
        return fallback


def _local_finance_answer(message: str, intent: str) -> str:
    variants = [
        "Mình hiểu câu hỏi của bạn theo hướng {intent}. Nói ngắn gọn:",
        "Câu này không cần ép thành phân tích cổ phiếu. Mình giải thích theo góc nhìn tài chính:",
        "Để dễ hình dung, mình tách ý chính như sau:",
    ]
    opener = random.choice(variants).format(intent=intent.replace("_", " "))
    lower = _lower_text(message)

    if any(term in lower for term in ("vĩ mô", "vi mo", "macro", "kinh tế", "kinh te")):
        body = (
            "kinh tế vĩ mô là bức tranh lớn của nền kinh tế: tăng trưởng GDP, lạm phát, lãi suất, "
            "tỷ giá, việc làm, tiêu dùng và chính sách tiền tệ/tài khóa. Với nhà đầu tư, vĩ mô giúp "
            "hiểu môi trường dòng tiền: lãi suất cao thường gây áp lực lên định giá, còn tăng trưởng "
            "ổn định và lạm phát hạ nhiệt thường hỗ trợ tâm lý thị trường."
        )
    elif "tin" in lower or "news" in lower:
        body = (
            "tin tài chính nên được đọc theo ba lớp: sự kiện xảy ra là gì, nó ảnh hưởng tới lợi nhuận "
            "hoặc dòng tiền ra sao, và thị trường đã phản ánh bao nhiêu vào giá. Nếu bạn đưa mã cổ phiếu "
            "hoặc thị trường cụ thể, mình có thể nối thêm dữ liệu Yahoo/Finnhub/FireAnt."
        )
    else:
        body = (
            "một khái niệm tài chính nên được nhìn qua định nghĩa, ví dụ thực tế và rủi ro khi áp dụng. "
            "Nếu bạn hỏi một thuật ngữ cụ thể, mình sẽ giải thích bằng ngôn ngữ đời thường và liên hệ với "
            "quyết định đầu tư hoặc quản lý tiền cá nhân."
        )

    return f"{opener}\n\n{body}\n\nLưu ý: đây là thông tin giáo dục, không phải khuyến nghị đầu tư cá nhân."


async def general_finance_chat(message: str, intent: str, history: list[Any] | None = None) -> dict[str, Any]:
    fallback = _local_finance_answer(message, intent)
    system = (
        "Bạn là trợ lý AI tài chính nói tiếng Việt tự nhiên. Trả lời linh hoạt, có tính giáo dục, "
        "không bịa số liệu thị trường, không đưa khuyến nghị đầu tư cá nhân. Nếu câu hỏi là vĩ mô "
        "hoặc kiến thức tài chính, hãy giải thích rõ, có ví dụ ngắn và giọng trò chuyện."
    )
    history_text = "\n".join(
        f"{getattr(item, 'role', 'user')}: {getattr(item, 'content', '')}" for item in (history or [])[-6:]
    )
    answer = await _call_llm(
        system,
        f"Lịch sử gần đây:\n{history_text}\n\nCâu hỏi hiện tại: {message}",
        fallback,
    )
    return {
        "answer": answer,
        "analysis": {"intent": intent, "mode": "general_finance_chat"},
        "retrieval": {"intent": intent, "symbols": [], "bundles": []},
        "citations": [],
        "market_data": [],
    }


async def _market_index_chat(message: str) -> dict[str, Any]:
    requested = _index_symbol_from_message(message)
    if requested:
        symbols = [requested]
    else:
        symbols = ["^VNINDEX", "^DJI", "^IXIC"] if "chỉ số" in _lower_text(message) else []

    quotes: list[dict[str, Any]] = []
    if symbols:
        results = await asyncio.gather(*(_fetch_index_quote(symbol) for symbol in symbols), return_exceptions=True)
        for result in results:
            if isinstance(result, dict):
                quotes.append(result)
            else:
                logger.warning("Market index quote failed: %s", result)
    else:
        summary = await get_market_summary()
        quotes = [item for item in summary.get("indices", []) if isinstance(item, dict)]

    market_data = [_quote_to_market_card(quote) for quote in quotes]
    return {
        "answer": _market_index_answer(message, quotes),
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


async def generate_chat_reply(message: str, conversation_id: str, history: list[Any]) -> dict[str, Any]:
    save_chat_message(conversation_id, "user", message)
    intent = intent_classifier(message)
    logger.info("Detected chat intent=%s conversation_id=%s message=%r", intent, conversation_id, message[:160])

    symbols = detect_symbols(message)

    if intent == "market_index":
        pipeline_result = await _market_index_chat(message)
    elif intent == "stock_analysis":
        pipeline_result = await FinancialRAGPipeline().run(message, use_llm=bool(get_settings().hf_token))
    elif intent == "news_query" and symbols:
        pipeline_result = await FinancialRAGPipeline().run(message, use_llm=False)
        pipeline_result["answer"] = _news_answer_from_retrieval(message, pipeline_result.get("retrieval", {}))
    elif intent in {"macroeconomics", "finance_education", "news_query", "general_ai_chat"}:
        pipeline_result = await general_finance_chat(message, intent, history)
    else:
        pipeline_result = await general_finance_chat(message, "general_ai_chat", history)

    reply = pipeline_result["answer"]
    market_data = pipeline_result.get("market_data")
    if market_data is None:
        market_data = pipeline_result.get("retrieval", {}).get("bundles", [])

    assistant_message = save_chat_message(
        conversation_id,
        "assistant",
        reply,
        market_data,
    )
    return {
        "reply": reply,
        "answer": reply,
        "intent": intent,
        "market_data": market_data,
        "citations": pipeline_result.get("citations", []),
        "sources_used": pipeline_result.get("citations", []),
        "analysis": pipeline_result.get("analysis"),
        "retrieval": pipeline_result.get("retrieval"),
        "message": assistant_message,
    }
