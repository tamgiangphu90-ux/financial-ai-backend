import asyncio
from typing import Any

import requests

from ai.financial_analyst import FinancialAnalyst
from retrieval.retriever import RetrievalEngine
from retrieval.source_verifier import verify_retrieval_bundle
from utils.config import get_settings


def _citations(retrieval: dict[str, Any]) -> list[dict[str, Any]]:
    citations = []
    for bundle in retrieval.get("bundles", []):
        for quote in bundle.get("quotes", []):
            citations.append(
                {
                    "source": quote.get("source"),
                    "symbol": bundle.get("symbol"),
                    "url": quote.get("url"),
                    "market_time": quote.get("market_time"),
                }
            )
        for item in bundle.get("news", [])[:5]:
            citations.append(
                {
                    "source": item.get("source") or "Finnhub",
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "published_date": item.get("published_date"),
                }
            )
    if retrieval.get("market_summary"):
        citations.append({"source": "Yahoo Finance", "type": "market_summary"})
    return [item for item in citations if item.get("source")]


class FinancialRAGPipeline:
    def __init__(self) -> None:
        self.retriever = RetrievalEngine()
        self.analyst = FinancialAnalyst()

    async def run(self, message: str, symbol: str | None = None, use_llm: bool = True) -> dict[str, Any]:
        retrieval = await self.retriever.retrieve(message, symbol=symbol)
        for bundle in retrieval.get("bundles", []):
            verify_retrieval_bundle(bundle)

        analysis = self.analyst.analyze_retrieval(retrieval)
        answer = self._deterministic_answer(message, retrieval, analysis)
        if use_llm:
            answer = await self._grounded_llm_answer(message, retrieval, analysis, answer)

        return {
            "answer": answer,
            "language": retrieval.get("language"),
            "intent": retrieval.get("intent"),
            "symbols": retrieval.get("symbols", []),
            "analysis": analysis,
            "retrieval": retrieval,
            "citations": _citations(retrieval),
        }

    def _deterministic_answer(self, message: str, retrieval: dict[str, Any], analysis: dict[str, Any]) -> str:
        language = retrieval.get("language", "en")
        analyses = analysis.get("analyses", [])

        if not analyses:
            if language == "vi":
                return (
                    "Mình chưa xác định được mã cổ phiếu cụ thể trong câu hỏi. "
                    "Dữ liệu thị trường tổng quan đã được truy xuất nếu có, nhưng để phân tích sâu bạn nên nêu rõ mã như VNM, FPT, AAPL hoặc NVDA."
                )
            return (
                "I could not identify a specific stock symbol in your question. "
                "I retrieved broad market context where possible, but a symbol such as AAPL, NVDA, FPT, or VNM will enable deeper analysis."
            )

        blocks = []
        for item in analyses:
            verification = item.get("verification") or {}
            discrepancies = verification.get("discrepancies") or []
            if language == "vi":
                trend_label = self._label("trend", item["trend"], language)
                recommendation_label = self._label("recommendation", item["recommendation"], language)
                risk_label = self._label("risk", item["risk_level"], language)
                block = (
                    f"{item['symbol']}: xu hướng {trend_label}, khuyến nghị {recommendation_label}, "
                    f"rủi ro {risk_label}, giá tham chiếu {item.get('price')}. "
                    f"Độ tin cậy nguồn: {item.get('confidence')}. {item.get('reasoning')}"
                )
                if discrepancies:
                    block += " Lưu ý chênh lệch nguồn: " + " ".join(
                        self._translate_discrepancy(text) for text in discrepancies[:2]
                    )
            else:
                block = (
                    f"{item['symbol']}: trend {item['trend']}, recommendation {item['recommendation']}, "
                    f"risk {item['risk_level']}, reference price {item.get('price')}. "
                    f"Source confidence: {item.get('confidence')}. {item.get('reasoning')}"
                )
                if discrepancies:
                    block += " Source discrepancy note: " + " ".join(discrepancies[:2])
            blocks.append(block)

        disclaimer = (
            " Đây là phân tích dữ liệu thị trường, không phải lời khuyên đầu tư cá nhân."
            if language == "vi"
            else " This is market analysis, not personalized investment advice."
        )
        return "\n\n".join(blocks) + disclaimer

    def _label(self, kind: str, value: str, language: str) -> str:
        if language != "vi":
            return value
        labels = {
            "trend": {"bullish": "tăng", "bearish": "giảm", "neutral": "trung tính"},
            "recommendation": {
                "buy": "cân nhắc mua",
                "watch": "theo dõi",
                "hold": "nắm giữ/quan sát",
                "avoid": "tránh mua mới",
            },
            "risk": {"low": "thấp", "medium": "trung bình", "high": "cao"},
        }
        return labels.get(kind, {}).get(value, value)

    def _translate_discrepancy(self, text: str) -> str:
        if text == "Only one price source was available, so confidence is capped.":
            return "Chỉ có một nguồn giá khả dụng nên độ tin cậy bị giới hạn."
        return (
            text.replace("price", "giá")
            .replace("differs from median", "khác trung vị")
            .replace("by more than 2%", "hơn 2%")
        )

    async def _grounded_llm_answer(
        self,
        message: str,
        retrieval: dict[str, Any],
        analysis: dict[str, Any],
        fallback: str,
    ) -> str:
        settings = get_settings()
        if not settings.hf_token:
            return fallback

        language = retrieval.get("language", "en")
        language_rule = "Answer entirely in Vietnamese." if language == "vi" else "Answer entirely in English."
        system = (
            "You are a realtime financial research copilot. Use only the supplied retrieval and analysis data. "
            "Do not invent prices, news, sources, or forecasts. Mention source discrepancies when present. "
            f"{language_rule} Keep the answer concise, analytical, and include a non-personal-advice caveat."
        )
        payload = {
            "model": settings.hf_model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"Question: {message}\n\n"
                        f"Verified retrieval: {retrieval}\n\n"
                        f"Financial analysis: {analysis}\n\n"
                        f"Draft answer: {fallback}"
                    ),
                },
            ],
            "max_tokens": 550,
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
            result = response.json()
            if response.status_code >= 400:
                return fallback
            return result["choices"][0]["message"]["content"].strip() or fallback
        except Exception:
            return fallback
