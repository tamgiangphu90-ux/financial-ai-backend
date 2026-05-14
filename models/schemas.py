from typing import Any, Literal

from pydantic import BaseModel, Field


class StockQuote(BaseModel):
    symbol: str
    current_price: float | None = None
    previous_close: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    volume: int | None = None
    market_cap: int | float | None = None
    currency: str | None = None
    fifty_two_week_range: dict[str, float | None]
    exchange: str | None = None
    source: str = "Yahoo Finance"


class NewsItem(BaseModel):
    title: str
    summary: str | None = None
    source: str | None = None
    published_date: str | None = None
    url: str | None = None
    sentiment: dict[str, Any] | None = None


class AnalyzeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=24)


class AnalyzeResponse(BaseModel):
    symbol: str
    trend: Literal["bullish", "bearish", "neutral"]
    recommendation: Literal["buy", "watch", "hold", "avoid"]
    risk_level: Literal["low", "medium", "high"]
    analysis: str
    price: float | None = None
    signals: list[str] = []
    data_sources: list[str] = []


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"
    history: list[HistoryMessage] = []


class FeedbackRequest(BaseModel):
    user_id: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    feedback_type: str | None = None
    correction: str | None = None
    metadata: dict[str, Any] = {}


class WatchlistRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    symbol: str = Field(min_length=1, max_length=32)
    market: str | None = None
    notes: str | None = None
