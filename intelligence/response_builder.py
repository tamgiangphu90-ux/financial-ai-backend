from typing import Any


DISCLAIMER = "Thông tin chỉ mang tính tham khảo, không phải khuyến nghị đầu tư."


def build_api_response(
    summary: str,
    analysis: str,
    trend: str = "neutral",
    risk_level: str = "medium",
    confidence_score: float = 0.0,
    sources: list[dict[str, Any]] | None = None,
    source_status: dict[str, str] | None = None,
    related_topics: list[str] | None = None,
    next_questions: list[str] | None = None,
) -> dict[str, Any]:
    source_list = sources or []
    return {
        "summary": summary,
        "analysis": analysis,
        "trend": trend,
        "risk_level": risk_level,
        "confidence_score": confidence_score,
        "source_count": len(source_list),
        "sources": source_list,
        "source_status": source_status or {},
        "related_topics": related_topics or [],
        "next_questions": next_questions or [],
        "disclaimer": DISCLAIMER,
    }


def build_text_answer(response: dict[str, Any]) -> str:
    source_names = ", ".join({str(item.get("source")) for item in response.get("sources", []) if item.get("source")}) or "Chưa có nguồn dữ liệu xác nhận"
    return (
        f"1. Tóm tắt\n{response['summary']}\n\n"
        f"2. Dữ liệu chính\nNguồn: {source_names}. Độ tin cậy: {response['confidence_score']}.\n\n"
        f"3. Phân tích\n{response['analysis']}\n\n"
        f"4. Rủi ro\nMức rủi ro: {response['risk_level']}.\n\n"
        f"5. Kết luận\n{response['disclaimer']}\n\n"
        f"6. Nguồn tham khảo\n{source_names}"
    )
