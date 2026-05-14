from typing import Any


def reason_about_market(summary: dict[str, Any] | None, movers: dict[str, Any] | None = None) -> dict[str, Any]:
    indices = (summary or {}).get("indices", [])
    mover_items = (movers or {}).get("movers", [])
    return {
        "summary": f"Đã tổng hợp {len(indices)} chỉ số/tài sản và {len(mover_items)} mã biến động mạnh.",
        "indices": indices,
        "top_movers": mover_items,
        "risk_level": "medium",
        "confidence_score": 0.72 if indices or mover_items else 0.0,
    }
