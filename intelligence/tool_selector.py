from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSelection:
    name: str
    use_rag: bool = False
    use_llm: bool = False


class ToolSelector:
    def select(self, intent: str, has_symbols: bool, llm_configured: bool) -> ToolSelection:
        if intent == "market_index":
            return ToolSelection(name="market_index_tool")
        if intent in {"stock_analysis", "financial_report"}:
            return ToolSelection(name="financial_rag_pipeline", use_rag=True, use_llm=llm_configured)
        if intent == "news_query":
            return ToolSelection(name="news_rag_pipeline", use_rag=True, use_llm=False)
        return ToolSelection(name="general_finance_chat", use_llm=llm_configured)
