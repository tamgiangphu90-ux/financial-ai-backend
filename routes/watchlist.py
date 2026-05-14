from fastapi import APIRouter

from database.session import sqlite_execute
from models.schemas import WatchlistRequest


router = APIRouter(tags=["watchlist"])


@router.get("/watchlist/{user_id}")
async def get_watchlist(user_id: str):
    rows = sqlite_execute("SELECT * FROM watchlists WHERE user_id = ? ORDER BY id DESC", (user_id,))
    return {"user_id": user_id, "watchlist": rows}


@router.post("/watchlist")
async def add_watchlist(request: WatchlistRequest):
    symbol = request.symbol.upper().strip()
    sqlite_execute(
        """
        INSERT INTO watchlists (user_id, symbol, market, notes)
        VALUES (?, ?, ?, ?)
        """,
        (request.user_id, symbol, request.market, request.notes),
    )
    return {"status": "ok", "user_id": request.user_id, "symbol": symbol}
