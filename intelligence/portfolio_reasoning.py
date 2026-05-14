from typing import Any


def portfolio_overview(watchlist: list[dict[str, Any]]) -> dict[str, Any]:
    symbols = [item.get("symbol") for item in watchlist]
    return {
        "summary": f"Danh mục theo dõi có {len(symbols)} mã.",
        "symbols": symbols,
        "risk_level": "medium" if symbols else "low",
        "next_questions": ["Bạn muốn kiểm tra rủi ro tập trung theo ngành hay theo thị trường?"],
    }
