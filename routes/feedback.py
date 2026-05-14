from fastapi import APIRouter

from feedback.feedback_collector import FeedbackCollector
from feedback.response_quality_monitor import ResponseQualityMonitor
from models.schemas import FeedbackRequest


router = APIRouter(tags=["feedback"])


@router.post("/feedback")
async def feedback(request: FeedbackRequest):
    result = FeedbackCollector().collect(request.model_dump())
    quality = ResponseQualityMonitor().inspect(
        {
            "confidence_score": (request.metadata or {}).get("confidence_score", 0.0),
            "sources": (request.metadata or {}).get("sources", []),
            "disclaimer": (request.metadata or {}).get("disclaimer", ""),
        }
    )
    return {**result, "quality": quality}
