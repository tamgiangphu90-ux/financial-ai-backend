from dataclasses import asdict, dataclass

from intelligence.intent_router import intent_classifier
from retrieval.retriever import detect_symbols, is_vietnam_market
from retrieval.source_registry import sources_for


@dataclass(frozen=True)
class QueryPlan:
    intent: str
    symbols: list[str]
    sources: list[str]
    needs_realtime: bool
    needs_macro: bool
    needs_company_reports: bool
    needs_news: bool
    region: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def build_query_plan(message: str) -> QueryPlan:
    intent = intent_classifier(message)
    symbols = detect_symbols(message)
    region = "Vietnam" if any(is_vietnam_market(symbol, message) for symbol in symbols) else None
    needs_realtime = intent in {"stock_analysis", "market_index", "risk_analysis", "portfolio_questions"} or bool(symbols)
    needs_macro = intent == "macroeconomics"
    needs_company_reports = intent in {"financial_report", "company_fundamentals"}
    needs_news = intent == "news_query" or "news" in message.lower() or "tin" in message.lower()

    data_types: set[str] = set()
    if needs_realtime:
        data_types.update({"quote", "index", "market_data"})
    if needs_macro:
        data_types.update({"macro", "rates", "gdp", "cpi"})
    if needs_company_reports:
        data_types.update({"reports", "fundamentals"})
    if needs_news:
        data_types.add("news")

    if not data_types:
        data_types.add("news")

    source_names = [source.name for source in sources_for(data_types, region=region)]
    if not source_names:
        source_names = [source.name for source in sources_for(data_types)]

    return QueryPlan(
        intent=intent,
        symbols=symbols,
        sources=source_names[:8],
        needs_realtime=needs_realtime,
        needs_macro=needs_macro,
        needs_company_reports=needs_company_reports,
        needs_news=needs_news,
        region=region,
    )
