from typing import Any


def macro_snapshot() -> dict[str, Any]:
    return {
        "summary": "Macro layer is ready for SBV, GSO, World Bank, IMF and FRED connectors.",
        "active_sources": [],
        "placeholder_sources": ["State Bank of Vietnam", "General Statistics Office of Vietnam", "World Bank", "IMF", "FRED"],
        "risk_level": "medium",
        "confidence_score": 0.0,
        "warning": "No live macro connector is enabled yet; values are not inferred.",
    }
