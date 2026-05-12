from typing import Any


POSITIVE_WORDS = (
    "upgrade",
    "growth",
    "profit",
    "beat",
    "record",
    "surge",
    "strong",
    "tăng",
    "lãi",
    "tích cực",
)
NEGATIVE_WORDS = (
    "downgrade",
    "loss",
    "miss",
    "weak",
    "fall",
    "risk",
    "lawsuit",
    "giảm",
    "lỗ",
    "tiêu cực",
)


def _float(value: Any) -> float | None:
    if value in (None, "", "N/A"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _best_quote(bundle: dict[str, Any]) -> dict[str, Any] | None:
    primary_source = (bundle.get("verification") or {}).get("primary_source")
    for quote in bundle.get("quotes", []):
        if quote.get("source") == primary_source:
            return quote
    quotes = bundle.get("quotes", [])
    return quotes[0] if quotes else None


def score_sentiment(news: list[dict[str, Any]]) -> int:
    score = 0
    for item in news[:12]:
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        score += sum(1 for word in POSITIVE_WORDS if word in text)
        score -= sum(1 for word in NEGATIVE_WORDS if word in text)
    return score


class FinancialAnalyst:
    def analyze_bundle(self, bundle: dict[str, Any], language: str = "en") -> dict[str, Any]:
        quote = _best_quote(bundle) or {}
        verification = bundle.get("verification") or {}
        news = bundle.get("news") or []
        signals: list[str] = []
        score = 0

        price = _float(verification.get("primary_price") or quote.get("current_price"))
        previous_close = _float(quote.get("previous_close"))
        day_high = _float(quote.get("day_high"))
        day_low = _float(quote.get("day_low"))
        volume = _float(quote.get("volume"))
        change_percent = _float(quote.get("change_percent"))

        if previous_close and price is not None:
            change_percent = (price - previous_close) / previous_close * 100

        if change_percent is not None:
            if change_percent > 1.5:
                score += 2
                signals.append(self._text(language, f"Price momentum is positive at {change_percent:.2f}%.", f"Động lượng giá tích cực, tăng {change_percent:.2f}%."))
            elif change_percent < -1.5:
                score -= 2
                signals.append(self._text(language, f"Price momentum is negative at {change_percent:.2f}%.", f"Động lượng giá tiêu cực, giảm {abs(change_percent):.2f}%."))
            else:
                signals.append(self._text(language, "Price action is mostly neutral.", "Diễn biến giá đang khá trung tính."))

        if day_high and day_low and price:
            volatility = (day_high - day_low) / price * 100
            if volatility > 3:
                score -= 1
                signals.append(self._text(language, f"Intraday volatility is elevated at {volatility:.2f}%.", f"Biến động trong phiên cao, khoảng {volatility:.2f}%."))
            else:
                signals.append(self._text(language, f"Intraday volatility is contained at {volatility:.2f}%.", f"Biến động trong phiên ở mức kiểm soát, khoảng {volatility:.2f}%."))

        if volume:
            signals.append(self._text(language, f"Reported volume is {volume:,.0f}.", f"Khối lượng ghi nhận khoảng {volume:,.0f}."))

        sentiment_score = score_sentiment(news)
        score += sentiment_score
        if news:
            signals.append(self._text(language, f"News sentiment score is {sentiment_score}.", f"Điểm cảm tính tin tức là {sentiment_score}."))

        confidence = _float(verification.get("confidence")) or 0
        if confidence < 0.65:
            score -= 1
            signals.append(self._text(language, "Source confidence is limited due to missing or divergent data.", "Độ tin cậy dữ liệu còn hạn chế do thiếu nguồn hoặc có chênh lệch."))

        if score >= 2:
            trend = "bullish"
            recommendation = "watch"
        elif score <= -2:
            trend = "bearish"
            recommendation = "avoid"
        else:
            trend = "neutral"
            recommendation = "hold"

        risk_level = "medium"
        if confidence < 0.6 or abs(score) >= 4:
            risk_level = "high"
        elif trend == "neutral" and confidence >= 0.75:
            risk_level = "low"

        reasoning = self._reasoning(language, bundle.get("symbol"), trend, recommendation, risk_level, signals)
        return {
            "symbol": bundle.get("symbol"),
            "market": bundle.get("market"),
            "trend": trend,
            "recommendation": recommendation,
            "risk_level": risk_level,
            "price": price,
            "confidence": confidence,
            "signals": signals,
            "reasoning": reasoning,
            "verification": verification,
            "news_count": len(news),
        }

    def analyze_retrieval(self, retrieval: dict[str, Any]) -> dict[str, Any]:
        language = retrieval.get("language", "en")
        analyses = [self.analyze_bundle(bundle, language) for bundle in retrieval.get("bundles", [])]
        return {
            "language": language,
            "intent": retrieval.get("intent"),
            "analyses": analyses,
            "market_summary": retrieval.get("market_summary"),
            "top_movers": retrieval.get("top_movers"),
        }

    def _text(self, language: str, en: str, vi: str) -> str:
        return vi if language == "vi" else en

    def _reasoning(self, language: str, symbol: str, trend: str, recommendation: str, risk: str, signals: list[str]) -> str:
        if language == "vi":
            trend_label = {"bullish": "tăng", "bearish": "giảm", "neutral": "trung tính"}[trend]
            recommendation_label = {
                "buy": "cân nhắc mua",
                "watch": "theo dõi",
                "hold": "nắm giữ/quan sát",
                "avoid": "tránh mua mới",
            }[recommendation]
            risk_label = {"low": "thấp", "medium": "trung bình", "high": "cao"}[risk]
            return (
                f"{symbol} đang nghiêng về xu hướng {trend_label}. "
                f"Khuyến nghị hệ thống: {recommendation_label}, mức rủi ro: {risk_label}. "
                f"Các tín hiệu chính: {' '.join(signals[:4])}"
            )
        return (
            f"{symbol} currently leans {trend}. "
            f"System recommendation: {recommendation}, risk level: {risk}. "
            f"Key signals: {' '.join(signals[:4])}"
        )
