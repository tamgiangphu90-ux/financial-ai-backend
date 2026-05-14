from typing import Any

from ai.financial_analyst import FinancialAnalyst


class FinancialReasoner:
    def __init__(self) -> None:
        self.analyst = FinancialAnalyst()

    def reason(self, retrieval: dict[str, Any]) -> dict[str, Any]:
        analysis = self.analyst.analyze_retrieval(retrieval)
        analyses = analysis.get("analyses", [])
        risk_levels = [item.get("risk_level") for item in analyses if item.get("risk_level")]
        confidence_values = [
            float(item.get("confidence") or 0)
            for item in analyses
            if item.get("confidence") is not None
        ]
        return {
            **analysis,
            "summary": self._summary(analyses),
            "key_factors": self._key_factors(analyses),
            "opportunities": self._opportunities(analyses),
            "risks": self._risks(analyses),
            "risk_level": "high" if "high" in risk_levels else "medium" if "medium" in risk_levels else "low",
            "confidence_score": round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 0.0,
            "next_questions": self._next_questions(analyses),
        }

    def _summary(self, analyses: list[dict[str, Any]]) -> str:
        if not analyses:
            return "Chưa có đủ dữ liệu định lượng để kết luận."
        return "; ".join(f"{item.get('symbol')}: {item.get('trend')}" for item in analyses)

    def _key_factors(self, analyses: list[dict[str, Any]]) -> list[str]:
        factors = []
        for item in analyses:
            factors.extend(item.get("signals", [])[:3])
        return factors[:8]

    def _opportunities(self, analyses: list[dict[str, Any]]) -> list[str]:
        return [f"{item.get('symbol')}: theo dõi khi xu hướng và độ tin cậy dữ liệu cải thiện." for item in analyses if item.get("trend") != "bearish"]

    def _risks(self, analyses: list[dict[str, Any]]) -> list[str]:
        risks = []
        for item in analyses:
            if item.get("risk_level") == "high":
                risks.append(f"{item.get('symbol')}: rủi ro dữ liệu hoặc biến động cao.")
            discrepancies = (item.get("verification") or {}).get("discrepancies") or []
            risks.extend(discrepancies[:2])
        return risks[:8]

    def _next_questions(self, analyses: list[dict[str, Any]]) -> list[str]:
        symbols = [item.get("symbol") for item in analyses if item.get("symbol")]
        if not symbols:
            return ["Bạn muốn phân tích mã cổ phiếu, chỉ số hay yếu tố vĩ mô nào?"]
        symbol = symbols[0]
        return [
            f"Tin tức mới nhất ảnh hưởng tới {symbol} là gì?",
            f"Rủi ro chính của {symbol} trong ngắn hạn là gì?",
            f"So sánh {symbol} với các mã cùng ngành như thế nào?",
        ]
