import unittest

from intelligence.intent_router import intent_classifier
from rag.pipeline import FinancialRAGPipeline


class IntelligenceExampleTests(unittest.TestCase):
    def test_requested_example_intents(self):
        examples = {
            "kinh tế vĩ mô là gì": "macroeconomics",
            "VNINDEX hôm nay thế nào": "market_index",
            "phân tích VCB": "stock_analysis",
            "báo cáo tài chính VNM": "financial_report",
            "tin tức chứng khoán hôm nay": "news_query",
        }

        for message, expected in examples.items():
            with self.subTest(message=message):
                self.assertEqual(intent_classifier(message), expected)

    def test_no_market_data_fallback_is_educational_and_structured(self):
        answer = FinancialRAGPipeline()._deterministic_answer(
            "báo cáo tài chính VNM",
            {"language": "vi", "intent": "financial_report", "bundles": []},
            {"analyses": []},
        )

        for heading in ("Tóm tắt", "Dữ liệu", "Phân tích", "Rủi ro", "Kết luận"):
            self.assertIn(heading, answer)
        self.assertIn("khung phân tích", answer)
        self.assertNotIn("vui lòng cung cấp mã", answer.lower())

    def test_rag_answer_includes_source_names(self):
        retrieval = {
            "language": "vi",
            "intent": "analysis",
            "symbols": ["VCB"],
            "bundles": [
                {
                    "symbol": "VCB",
                    "quotes": [{"source": "Yahoo Finance", "current_price": 90000}],
                    "news": [{"source": "Finnhub", "title": "VCB update"}],
                }
            ],
        }
        analysis = {
            "analyses": [
                {
                    "symbol": "VCB",
                    "trend": "neutral",
                    "recommendation": "hold",
                    "risk_level": "medium",
                    "price": 90000,
                    "confidence": 0.7,
                    "reasoning": "Dữ liệu hiện tại chưa tạo tín hiệu quá mạnh.",
                    "verification": {"discrepancies": []},
                }
            ]
        }

        answer = FinancialRAGPipeline()._deterministic_answer("phân tích VCB", retrieval, analysis)

        self.assertIn("Yahoo Finance", answer)
        self.assertIn("Finnhub", answer)
        self.assertIn("Tóm tắt", answer)
        self.assertIn("Kết luận", answer)


if __name__ == "__main__":
    unittest.main()
