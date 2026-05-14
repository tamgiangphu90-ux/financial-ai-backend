from typing import Any


class ResponseQualityMonitor:
    def inspect(self, response: dict[str, Any]) -> dict[str, Any]:
        warnings = []
        if response.get("confidence_score", 0) < 0.5:
            warnings.append("Low confidence response.")
        if not response.get("sources"):
            warnings.append("No cited source.")
        if "khuyến nghị đầu tư" not in response.get("disclaimer", "").lower():
            warnings.append("Missing investment disclaimer.")
        return {"warnings": warnings, "quality_score": max(0.0, 1.0 - 0.2 * len(warnings))}
