from fastapi import APIRouter

from services.cafef_service import get_cafef_stock_data
from services.finnhub_service import get_company_news
from services.fireant_service import FireAntError, get_vietnam_stock_data
from services.yahoo_service import get_market_summary, get_stock_quote, get_top_movers
from intelligence.macro_reasoning import macro_snapshot
from intelligence.market_reasoning import reason_about_market
from intelligence.response_builder import build_api_response
from utils.errors import ServiceError


router = APIRouter(tags=["market"])


@router.get("/stock/{symbol}")
async def stock(symbol: str):
    return await get_stock_quote(symbol)


@router.get("/market-data/{symbol}", include_in_schema=False)
async def legacy_market_data(symbol: str):
    return await get_stock_quote(symbol)


@router.get("/news/{symbol}")
async def news(symbol: str):
    return {"symbol": symbol.upper(), "news": await get_company_news(symbol)}


@router.get("/vn-stock/{symbol}")
async def vn_stock(symbol: str):
    cafef_data = None
    try:
        fireant_data = get_vietnam_stock_data(symbol)
        try:
            cafef_data = await get_cafef_stock_data(symbol)
        except ServiceError:
            cafef_data = None
        return {
            **fireant_data,
            "supplemental_sources": [cafef_data] if cafef_data else [],
        }
    except ValueError as exc:
        raise ServiceError(str(exc), status_code=400, code="invalid_vn_symbol") from exc
    except FireAntError as exc:
        try:
            cafef_data = await get_cafef_stock_data(symbol)
            return {
                **cafef_data,
                "source": "CafeF",
                "warnings": [
                    *(cafef_data.get("warnings") or []),
                    f"FireAnt unavailable: {exc}",
                ],
                "supplemental_sources": [],
            }
        except ServiceError:
            raise ServiceError(str(exc), status_code=exc.status_code, code="fireant_error") from exc


@router.get("/vietnam-market-data/{symbol}", include_in_schema=False)
async def legacy_vietnam_market_data(symbol: str):
    return await vn_stock(symbol)


@router.get("/market-summary")
async def market_summary():
    return await get_market_summary()


@router.get("/top-movers")
async def top_movers():
    return await get_top_movers()


@router.get("/market/trending")
async def market_trending():
    summary, movers = await get_market_summary(), await get_top_movers()
    reasoning = reason_about_market(summary, movers)
    return build_api_response(
        summary=reasoning["summary"],
        analysis="Market trend scan uses active Yahoo Finance data and ranks large movers by absolute percentage change.",
        trend="neutral",
        risk_level=reasoning["risk_level"],
        confidence_score=reasoning["confidence_score"],
        sources=[{"source": "Yahoo Finance", "type": "market_summary"}],
        source_status={"Yahoo Finance": "active"},
        related_topics=["market breadth", "momentum", "volatility"],
        next_questions=["Chỉ số nào đang dẫn dắt thị trường?", "Mã nào biến động mạnh nhất hôm nay?"],
    ) | {"market": reasoning}


@router.get("/market/macro")
async def market_macro():
    snapshot = macro_snapshot()
    return build_api_response(
        summary=snapshot["summary"],
        analysis=snapshot["warning"],
        trend="neutral",
        risk_level=snapshot["risk_level"],
        confidence_score=snapshot["confidence_score"],
        sources=[],
        source_status={source: "placeholder" for source in snapshot["placeholder_sources"]},
        related_topics=["GDP", "CPI", "interest rates", "FX"],
        next_questions=["Bạn muốn xem dữ liệu vĩ mô Việt Nam hay toàn cầu?"],
    ) | {"macro": snapshot}
