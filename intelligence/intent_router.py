import re
import unicodedata

from retrieval.retriever import detect_symbols


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
RISK_WORDS = ("risk", "rủi ro", "rui ro", "drawdown", "volatility", "biến động", "bien dong")
PORTFOLIO_WORDS = ("portfolio", "danh mục", "danh muc", "watchlist", "phân bổ", "phan bo", "tỷ trọng", "ty trong")
FUNDAMENTAL_WORDS = ("fundamental", "fundamentals", "định giá", "dinh gia", "p/e", "eps", "roe", "roa", "book value")
FINANCIAL_REPORT_WORDS = (
    "báo cáo tài chính",
    "bao cao tai chinh",
    "bctc",
    "financial report",
    "financial statement",
    "balance sheet",
    "income statement",
    "cash flow",
    "doanh thu",
    "lợi nhuận",
    "loi nhuan",
    "biên lợi nhuận",
    "bien loi nhuan",
)
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


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return stripped.replace("\u0111", "d").replace("\u0110", "D")


def lower_text(text: str) -> str:
    lower = " ".join(text.lower().split())
    plain = " ".join(strip_accents(lower).split())
    return f"{lower} {plain}"


def index_symbol_from_message(message: str) -> str | None:
    upper = re.sub(r"\s+", " ", message.upper())
    for alias, symbol in INDEX_ALIASES.items():
        if alias in upper:
            return symbol
    if "SP500" in upper or "S&P 500" in upper:
        return "^GSPC"
    return None


def intent_classifier(message: str) -> str:
    """Classify the user's financial-chat intent before selecting tools."""
    lower = lower_text(message)
    symbols = detect_symbols(message)
    index_symbol = index_symbol_from_message(message)

    if any(word in lower for word in FINANCIAL_REPORT_WORDS):
        return "financial_report"
    if any(word in lower for word in PORTFOLIO_WORDS):
        return "portfolio_questions"
    if any(word in lower for word in RISK_WORDS):
        return "risk_analysis"
    if any(word in lower for word in FUNDAMENTAL_WORDS):
        return "company_fundamentals"
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
