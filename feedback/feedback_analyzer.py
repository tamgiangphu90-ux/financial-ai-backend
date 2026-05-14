from typing import Any


class FeedbackAnalyzer:
    def analyze(self, feedback: list[dict[str, Any]]) -> dict[str, Any]:
        negative = [item for item in feedback if (item.get("rating") or 0) <= 2 or item.get("feedback_type") == "down"]
        corrections = [item for item in feedback if item.get("correction")]
        return {
            "total": len(feedback),
            "negative_count": len(negative),
            "correction_count": len(corrections),
            "signals": {
                "hallucination_risk": bool(corrections),
                "weak_source_quality": any("source" in str(item.get("correction", "")).lower() for item in corrections),
                "bad_routing_decision": any("wrong intent" in str(item.get("correction", "")).lower() for item in corrections),
            },
        }
