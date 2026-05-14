from typing import Any

from ai.financial_analyst import FinancialAnalyst
from intelligence.financial_reasoner import FinancialReasoner
from intelligence.response_builder import build_api_response
from intelligence.response_formatter import source_names_from_retrieval, structured_no_market_data_answer
from llm.provider import LLMProvider
from retrieval.multi_source_retriever import MultiSourceRetriever
from retrieval.source_verifier import verify_retrieval_bundle


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
    if retrieval.get("top_movers"):
        citations.append({"source": "Yahoo Finance", "type": "top_movers"})
    return [item for item in citations if item.get("source")]


class FinancialRAGPipeline:
    def __init__(self) -> None:
        self.retriever = MultiSourceRetriever()
        self.analyst = FinancialAnalyst()
        self.reasoner = FinancialReasoner()

    async def run(self, message: str, symbol: str | None = None, use_llm: bool = True) -> dict[str, Any]:
        retrieval = await self.retriever.retrieve(message, symbol=symbol)
        for bundle in retrieval.get("bundles", []):
            verify_retrieval_bundle(bundle)

        analysis = self.reasoner.reason(retrieval)
        answer = self._deterministic_answer(message, retrieval, analysis)
        if use_llm and self._has_grounding_data(retrieval):
            answer = await self._grounded_llm_answer(message, retrieval, analysis, answer)

        first_analysis = (analysis.get("analyses") or [{}])[0]
        api_response = build_api_response(
            summary=analysis.get("summary") or answer[:240],
            analysis=first_analysis.get("reasoning") or analysis.get("summary") or answer,
            trend=first_analysis.get("trend", "neutral"),
            risk_level=analysis.get("risk_level", first_analysis.get("risk_level", "medium")),
            confidence_score=analysis.get("confidence_score", retrieval.get("confidence_score", 0.0)),
            sources=_citations(retrieval),
            source_status=retrieval.get("source_status", {}),
            related_topics=["momentum", "volatility", "source verification"],
            next_questions=analysis.get("next_questions", []),
        )

        return {
            "answer": answer,
            "api_response": api_response,
            "language": retrieval.get("language"),
            "intent": retrieval.get("intent"),
            "symbols": retrieval.get("symbols", []),
            "analysis": analysis,
            "retrieval": retrieval,
            "citations": _citations(retrieval),
        }

    def _deterministic_answer(self, _: str, retrieval: dict[str, Any], analysis: dict[str, Any]) -> str:
        language = retrieval.get("language", "en")
        intent = retrieval.get("intent", "analysis")
        analyses = analysis.get("analyses", [])
        source_text = ", ".join(source_names_from_retrieval(retrieval))

        if not analyses or not self._has_grounding_data(retrieval):
            return structured_no_market_data_answer(language, intent, source_text)

        data_lines = []
        analysis_lines = []
        risk_lines = []
        for item in analyses:
            verification = item.get("verification") or {}
            discrepancies = verification.get("discrepancies") or []
            bundle_sources = self._bundle_sources(retrieval, item.get("symbol")) or source_text

            if language == "vi":
                trend_label = self._label("trend", item["trend"], language)
                recommendation_label = self._label("recommendation", item["recommendation"], language)
                risk_label = self._label("risk", item["risk_level"], language)
                data_lines.append(
                    f"- {item['symbol']}: giá tham chiếu {item.get('price')}; nguồn: {bundle_sources or 'không rõ'}; "
                    f"độ tin cậy nguồn: {item.get('confidence')}."
                )
                analysis_lines.append(
                    f"- {item['symbol']}: xu hướng {trend_label}, khuyến nghị hệ thống {recommendation_label}. "
                    f"{item.get('reasoning')}"
                )
                risk_line = f"- {item['symbol']}: rủi ro {risk_label}."
                if discrepancies:
                    risk_line += " Lưu ý chênh lệch nguồn: " + " ".join(
                        self._translate_discrepancy(text) for text in discrepancies[:2]
                    )
                if intent == "financial_report":
                    risk_line += " Chưa có dữ liệu báo cáo tài chính chính thức trong pipeline, nên không kết luận về doanh thu/lợi nhuận nếu nguồn không cung cấp."
                risk_lines.append(risk_line)
            else:
                data_lines.append(
                    f"- {item['symbol']}: reference price {item.get('price')}; sources: {bundle_sources or 'unknown'}; "
                    f"source confidence: {item.get('confidence')}."
                )
                analysis_lines.append(
                    f"- {item['symbol']}: trend {item['trend']}, system recommendation {item['recommendation']}. "
                    f"{item.get('reasoning')}"
                )
                risk_line = f"- {item['symbol']}: risk level {item['risk_level']}."
                if discrepancies:
                    risk_line += " Source discrepancy note: " + " ".join(discrepancies[:2])
                if intent == "financial_report":
                    risk_line += " Official financial statement data is not available in this pipeline, so revenue/earnings claims are not inferred without a source."
                risk_lines.append(risk_line)

        if language == "vi":
            return (
                "Tóm tắt: Mình đã truy xuất dữ liệu trước khi phân tích và chỉ dùng các nguồn có trong kết quả truy xuất.\n\n"
                f"Dữ liệu:\n{chr(10).join(data_lines)}\n\n"
                f"Phân tích:\n{chr(10).join(analysis_lines)}\n\n"
                f"Rủi ro:\n{chr(10).join(risk_lines)}\n\n"
                "Kết luận: Đây là phân tích dữ liệu thị trường, không phải lời khuyên đầu tư cá nhân."
            )
        return (
            "Summary: I retrieved data before analysis and used only sources present in the retrieval result.\n\n"
            f"Data:\n{chr(10).join(data_lines)}\n\n"
            f"Analysis:\n{chr(10).join(analysis_lines)}\n\n"
            f"Risks:\n{chr(10).join(risk_lines)}\n\n"
            "Conclusion: This is market analysis, not personalized investment advice."
        )

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

    def _has_grounding_data(self, retrieval: dict[str, Any]) -> bool:
        if retrieval.get("market_summary") or retrieval.get("top_movers"):
            return True
        return any(bundle.get("quotes") or bundle.get("news") for bundle in retrieval.get("bundles", []))

    def _bundle_sources(self, retrieval: dict[str, Any], symbol: str | None) -> str:
        sources: list[str] = []
        for bundle in retrieval.get("bundles", []):
            if symbol and bundle.get("symbol") != symbol:
                continue
            for quote in bundle.get("quotes", []):
                source = quote.get("source")
                if source and source not in sources:
                    sources.append(source)
            for item in bundle.get("news", []):
                source = item.get("source") or "Finnhub"
                if source and source not in sources:
                    sources.append(source)
        return ", ".join(sources)

    async def _grounded_llm_answer(
        self,
        message: str,
        retrieval: dict[str, Any],
        analysis: dict[str, Any],
        fallback: str,
    ) -> str:
        language = retrieval.get("language", "en")
        language_rule = (
            "Answer entirely in Vietnamese because the user asked in Vietnamese."
            if language == "vi"
            else "Answer entirely in English."
        )
        system = (
            "You are a realtime financial research copilot. Use only the supplied retrieval and analysis data. "
            "Do not invent prices, news, financial statement facts, sources, forecasts, or URLs. "
            "If data is missing, say what is missing and answer educationally from the provided framework. "
            "Mention source names and source discrepancies when present. "
            f"{language_rule} Structure the answer with exactly these sections: Summary, Data, Analysis, Risks, Conclusion. "
            "Do not repeat the draft answer verbatim and do not return repeated fallback text."
        )
        user_prompt = (
            f"Question: {message}\n\n"
            f"Verified retrieval: {retrieval}\n\n"
            f"Financial analysis: {analysis}\n\n"
            f"Draft answer for grounding, not for copying: {fallback}"
        )
        return await LLMProvider().complete(system, user_prompt, fallback, max_tokens=650, temperature=0.45)
