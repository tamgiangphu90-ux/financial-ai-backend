from typing import Any

from rag.pipeline import FinancialRAGPipeline
from utils.errors import ServiceError


async def analyze_symbol(symbol: str) -> dict[str, Any]:
    cleaned = symbol.strip().upper().lstrip("$")
    if not cleaned:
        raise ServiceError("Symbol is required", status_code=400, code="invalid_symbol")

    result = await FinancialRAGPipeline().run(
        f"Analyze {cleaned} using realtime market data and news.",
        symbol=cleaned,
        use_llm=False,
    )
    analyses = result.get("analysis", {}).get("analyses", [])
    if not analyses:
        raise ServiceError(
            f"No market data available for {cleaned}",
            status_code=404,
            code="analysis_data_unavailable",
        )
    item = analyses[0]
    return {
        "symbol": item["symbol"],
        "trend": item["trend"],
        "recommendation": item["recommendation"],
        "risk_level": item["risk_level"],
        "analysis": item["reasoning"],
        "price": item["price"],
        "signals": item["signals"],
        "data_sources": [
            citation["source"]
            for citation in result.get("citations", [])
            if citation.get("source")
        ],
    }
