import random
from typing import Any

from .intent_router import lower_text


STRUCTURE_VI = ("Tóm tắt", "Dữ liệu", "Phân tích", "Rủi ro", "Kết luận")
STRUCTURE_EN = ("Summary", "Data", "Analysis", "Risks", "Conclusion")


def safe_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def quote_to_market_card(quote: dict[str, Any]) -> dict[str, Any]:
    price = safe_number(quote.get("current_price") or quote.get("price"))
    previous = safe_number(quote.get("previous_close"))
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


def market_index_answer(_: str, quotes: list[dict[str, Any]]) -> str:
    if not quotes:
        return (
            "Mình chưa lấy được dữ liệu chỉ số ngay lúc này. Bạn có thể thử lại sau vài phút, "
            "hoặc hỏi thêm về bối cảnh như lãi suất, dòng tiền hay nhóm ngành dẫn dắt."
        )

    lines = []
    for quote in quotes:
        card = quote_to_market_card(quote)
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


def news_answer_from_retrieval(_: str, retrieval: dict[str, Any]) -> str:
    items: list[dict[str, Any]] = []
    for bundle in retrieval.get("bundles", []):
        for item in bundle.get("news", [])[:5]:
            if isinstance(item, dict) and item.get("title"):
                items.append({**item, "symbol": bundle.get("symbol")})

    if not items:
        sources = source_names_from_retrieval(retrieval)
        source_text = ", ".join(sources) if sources else "Yahoo Finance/Finnhub khi có dữ liệu"
        return structured_no_market_data_answer("vi", "news_query", source_text)

    lines = []
    for item in items[:6]:
        source = item.get("source") or "nguồn tin"
        symbol = f"{item.get('symbol')}: " if item.get("symbol") else ""
        lines.append(f"- {symbol}{item.get('title')} ({source})")

    return (
        "Tóm tắt: Mình tìm được một số tin liên quan.\n\n"
        "Dữ liệu:\n"
        + "\n".join(lines)
        + "\n\nPhân tích: Hãy ưu tiên tin có ảnh hưởng trực tiếp tới doanh thu, lợi nhuận, "
        "dòng tiền hoặc rủi ro pháp lý; tiêu đề tích cực chưa chắc đồng nghĩa giá sẽ tăng ngay."
        "\n\nRủi ro: Tin tức có thể phản ánh chậm hoặc chưa đủ bối cảnh định giá."
        "\n\nKết luận: Dùng tin như tín hiệu bổ sung, không thay thế phân tích dữ liệu doanh nghiệp."
    )


def local_finance_answer(message: str, intent: str) -> str:
    variants = [
        "Mình hiểu câu hỏi của bạn theo hướng {intent}. Nói ngắn gọn:",
        "Câu này không cần ép thành phân tích cổ phiếu. Mình giải thích theo góc nhìn tài chính:",
        "Để dễ hình dung, mình tách ý chính như sau:",
    ]
    opener = random.choice(variants).format(intent=intent.replace("_", " "))
    lower = lower_text(message)

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

    return (
        f"Tóm tắt: {opener}\n\n"
        f"Dữ liệu: Không cần dữ liệu thị trường thời gian thực cho câu hỏi giáo dục này.\n\n"
        f"Phân tích: {body}\n\n"
        "Rủi ro: Khái niệm tài chính khi áp dụng thực tế còn phụ thuộc mục tiêu, thời hạn, khẩu vị rủi ro và bối cảnh thị trường.\n\n"
        "Kết luận: Đây là thông tin giáo dục, không phải khuyến nghị đầu tư cá nhân."
    )


def source_names_from_retrieval(retrieval: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    for bundle in retrieval.get("bundles", []):
        for quote in bundle.get("quotes", []):
            source = quote.get("source")
            if source and source not in sources:
                sources.append(source)
        for item in bundle.get("news", []):
            source = item.get("source") or "Finnhub"
            if source and source not in sources:
                sources.append(source)
    if retrieval.get("market_summary") and "Yahoo Finance" not in sources:
        sources.append("Yahoo Finance")
    if retrieval.get("top_movers") and "Yahoo Finance" not in sources:
        sources.append("Yahoo Finance")
    return sources


def structured_no_market_data_answer(language: str, intent: str, sources: str = "") -> str:
    if language == "vi":
        source_line = sources or "chưa có nguồn dữ liệu thị trường đủ rõ"
        topic = {
            "financial_report": "báo cáo tài chính",
            "news_query": "tin tức thị trường",
            "market_index": "chỉ số thị trường",
            "stock_analysis": "phân tích cổ phiếu",
        }.get(intent, "chủ đề tài chính")
        return (
            f"Tóm tắt: Mình chưa có đủ dữ liệu thị trường đáng tin cậy để kết luận cụ thể về {topic} ngay lúc này.\n\n"
            f"Dữ liệu: Nguồn đã kiểm tra/ưu tiên: {source_line}. Không có số liệu đủ chắc để trích dẫn như giá, báo cáo hoặc tin mới.\n\n"
            "Phân tích: Có thể tiếp cận theo hướng giáo dục: xác định câu hỏi chính, kiểm tra nguồn dữ liệu chính thức, "
            "so sánh xu hướng qua nhiều kỳ và chỉ ra yếu tố tác động trực tiếp tới doanh thu, lợi nhuận, dòng tiền hoặc định giá.\n\n"
            "Rủi ro: Trả lời bằng số liệu khi nguồn thiếu hoặc lỗi dễ tạo tín hiệu sai. Vì vậy mình không bịa giá, tin tức hoặc chỉ tiêu tài chính.\n\n"
            "Kết luận: Hãy xem đây là khung phân tích ban đầu; khi có mã cổ phiếu, kỳ báo cáo hoặc nguồn dữ liệu cụ thể, mình có thể phân tích sâu hơn."
        )

    return (
        f"Summary: I do not have enough reliable market data to make a specific call on {intent} right now.\n\n"
        f"Data: Checked/preferred sources: {sources or 'no reliable market source available'}. No price, report, or news item is solid enough to cite.\n\n"
        "Analysis: Use an educational frame: define the question, check primary sources, compare trends across periods, and connect data to revenue, earnings, cash flow, or valuation.\n\n"
        "Risks: Inventing figures or headlines when sources are missing would be misleading.\n\n"
        "Conclusion: Treat this as an analysis framework until a symbol, reporting period, or reliable source is available."
    )
