from fastapi import APIRouter

from ai.analysis_engine import analyze_symbol
from models.schemas import AnalyzeRequest, AnalyzeResponse


router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    return await analyze_symbol(request.symbol)

