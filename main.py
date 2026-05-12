import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.analysis import router as analysis_router
from routes.chat import router as chat_router
from routes.market import router as market_router
from memory.store import init_memory
from services.chat_service import init_db
from utils.config import get_settings
from utils.errors import register_exception_handlers


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Financial AI backend for Zalo Mini App market data, news, Vietnam stocks, and AI analysis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(market_router)
app.include_router(analysis_router)
app.include_router(chat_router)


@app.on_event("startup")
async def startup() -> None:
    init_db()
    init_memory()


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "environment": settings.environment,
        "services": {
            "yahoo_finance": True,
            "finnhub_configured": bool(settings.finnhub_api_key),
            "fireant_configured": bool(settings.fireant_token),
            "cafef": True,
            "ai_configured": bool(settings.hf_token),
            "rag_pipeline": True,
            "source_verification": True,
            "memory_ready": True,
        },
    }
