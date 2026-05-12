import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import requests

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    BeautifulSoup = None


REST_BASE_URL = os.getenv("FIREANT_REST_BASE_URL", "https://restv2.fireant.vn")
QUOTE_HUB_URL = os.getenv("FIREANT_QUOTE_HUB_URL", "https://tradestation.fireant.vn/quote")
REQUEST_TIMEOUT = int(os.getenv("FIREANT_REQUEST_TIMEOUT", "15"))
SIGNALR_SEPARATOR = "\x1e"


class FireAntError(Exception):
    status_code = 502


class FireAntConfigurationError(FireAntError):
    status_code = 500


class FireAntNotFoundError(FireAntError):
    status_code = 404


class FireAntUnavailableError(FireAntError):
    status_code = 502


def normalize_vietnam_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper().lstrip("$")

    if not cleaned:
        raise ValueError("Symbol is required")

    if not cleaned.replace(".", "").isalnum():
        raise ValueError("Symbol contains invalid characters")

    return cleaned.split(".", 1)[0]


def _to_datetime(value: Any) -> datetime | None:
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, (int, float)):
        timestamp = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    if isinstance(value, str):
        text = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    return None


def _as_number(value: Any) -> float | int | None:
    if value in ("", None):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return int(number) if number.is_integer() else number


def _round(value: Any, digits: int = 2) -> float | int | None:
    number = _as_number(value)

    if number is None:
        return None

    return round(float(number), digits)


class FireAntProvider:
    """FireAnt data adapter.

    FireAnt's public site currently uses restv2.fireant.vn for reference data
    and a SignalR quote hub for realtime prices/trades. Keeping those details in
    this provider lets routes switch to another vendor later with minimal churn.
    """

    def __init__(
        self,
        token: str | None = None,
        rest_base_url: str = REST_BASE_URL,
        quote_hub_url: str = QUOTE_HUB_URL,
        timeout: int = REQUEST_TIMEOUT,
    ):
        self.token = token or os.getenv("FIREANT_TOKEN")
        self.rest_base_url = rest_base_url.rstrip("/")
        self.quote_hub_url = quote_hub_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0",
            }
        )

        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def get_vietnam_stock_data(self, symbol: str) -> dict[str, Any]:
        normalized_symbol = normalize_vietnam_symbol(symbol)
        metadata = {}
        metadata_warning = None

        try:
            metadata = self.get_symbol_metadata(normalized_symbol)
        except FireAntError as exc:
            metadata_warning = str(exc)

        quote, quote_error = self.get_realtime_quote(normalized_symbol)
        trades, trades_error = self.get_trades(normalized_symbol)
        bars, bars_error = self.get_intraday_bars(normalized_symbol)

        warnings = [
            message
            for message in (quote_error, trades_error, bars_error)
            if message
        ]

        if metadata_warning:
            warnings.append(metadata_warning)

        if not quote and not bars:
            scraped, scrape_error = self.scrape_symbol_page(normalized_symbol)

            if scraped:
                return {
                    "symbol": normalized_symbol,
                    "name": scraped.get("name"),
                    "exchange": scraped.get("exchange"),
                    "current_price": scraped.get("current_price"),
                    "change": scraped.get("change"),
                    "change_percent": scraped.get("change_percent"),
                    "volume": scraped.get("volume"),
                    "market_cap": scraped.get("market_cap"),
                    "liquidity": scraped.get("liquidity"),
                    "currency": "VND",
                    "market_time": scraped.get("market_time"),
                    "trading_statistics": scraped.get("trading_statistics", {}),
                    "trading_data": {"trades": [], "intraday_bars": []},
                    "source": "FireAnt",
                    "warnings": [*warnings, "Used FireAnt page scraping fallback"],
                }

            detail = "; ".join([*warnings, scrape_error or "FireAnt did not return price data"])
            raise FireAntUnavailableError(detail)

        latest_bar = bars[-1] if bars else {}
        current_price = _round(
            (quote or {}).get("last")
            or (quote or {}).get("current")
            or latest_bar.get("close"),
            metadata.get("fractionDigits", 2) or 2,
        )
        reference_price = _round((quote or {}).get("basic") or latest_bar.get("open"))
        price_change = _round(
            (current_price - reference_price)
            if current_price is not None and reference_price is not None
            else (quote or {}).get("change")
        )
        change_percent = _round(
            (price_change / reference_price * 100)
            if price_change is not None and reference_price
            else (quote or {}).get("pricePercentChange")
        )
        volume = _as_number((quote or {}).get("totalVolume") or latest_bar.get("totalVolume"))
        shares_outstanding = _as_number(
            metadata.get("sharesOutstanding") or metadata.get("totalShares")
        )
        market_cap = _as_number((quote or {}).get("marketCap"))

        if market_cap is None and current_price is not None and shares_outstanding:
            market_cap = current_price * shares_outstanding

        total_value = _as_number((quote or {}).get("totalValue") or latest_bar.get("totalValue"))
        liquidity = {
            "total_value": total_value,
            "active_buy_volume": _as_number((quote or {}).get("activeBuyVolume")),
            "deal_volume": _as_number((quote or {}).get("dealVolume")),
            "volume_24h": _as_number((quote or {}).get("volume24h")),
        }

        return {
            "symbol": normalized_symbol,
            "name": metadata.get("name"),
            "exchange": metadata.get("exchange"),
            "current_price": current_price,
            "change": price_change,
            "change_percent": change_percent,
            "volume": volume,
            "market_cap": market_cap,
            "liquidity": liquidity,
            "currency": "VND",
            "market_time": self._market_time(quote, latest_bar),
            "trading_statistics": {
                "reference_price": reference_price,
                "high": _as_number(latest_bar.get("high")),
                "low": _as_number(latest_bar.get("low")),
                "open": _as_number(latest_bar.get("open")),
                "total_value": total_value,
                "trade_count": len(trades),
                "bar_count": len(bars),
            },
            "trading_data": {
                "trades": trades,
                "intraday_bars": bars,
            },
            "source": "FireAnt",
            "warnings": warnings,
        }

    def get_symbol_metadata(self, symbol: str) -> dict[str, Any]:
        data = self._rest_get(f"symbols/{symbol}")

        if not isinstance(data, dict) or not data.get("symbol"):
            raise FireAntNotFoundError(f"FireAnt symbol not found: {symbol}")

        return data

    def scrape_symbol_page(self, symbol: str) -> tuple[dict[str, Any] | None, str | None]:
        if BeautifulSoup is None:
            return None, "beautifulsoup4 is not installed for FireAnt scraping fallback"

        url = f"https://fireant.vn/ma-chung-khoan/{symbol}"

        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            return None, f"Cannot scrape FireAnt: {exc}"

        if response.status_code in {401, 403, 429}:
            return None, f"FireAnt blocked scraping fallback with status {response.status_code}"

        if response.status_code >= 400:
            return None, f"FireAnt scraping fallback failed with status {response.status_code}"

        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text(" ", strip=True)

        if "captcha" in page_text.lower() or "access denied" in page_text.lower():
            return None, "FireAnt blocked scraping fallback"

        payload = self._extract_next_data(soup)
        parsed = self._extract_stock_snapshot(payload, symbol) if payload else {}

        if not parsed:
            parsed = {"name": soup.title.string.strip() if soup.title and soup.title.string else None}

        if not any(parsed.get(key) is not None for key in ("current_price", "volume", "market_cap")):
            return None, "FireAnt page did not expose parseable market data"

        return parsed, None

    def _extract_next_data(self, soup: BeautifulSoup) -> Any:
        script = soup.find("script", id="__NEXT_DATA__")

        if not script or not script.string:
            return None

        try:
            return json.loads(script.string)
        except json.JSONDecodeError:
            return None

    def _extract_stock_snapshot(self, payload: Any, symbol: str) -> dict[str, Any]:
        matches: list[dict[str, Any]] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                candidate_symbol = str(value.get("symbol") or value.get("code") or "").upper()
                if candidate_symbol == symbol:
                    matches.append(value)

                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(payload)

        if not matches:
            return {}

        row = matches[0]
        current_price = _round(
            row.get("last")
            or row.get("price")
            or row.get("currentPrice")
            or row.get("close")
        )
        change = _round(row.get("change") or row.get("priceChange"))
        change_percent = _round(row.get("changePercent") or row.get("pricePercentChange"))
        volume = _as_number(row.get("volume") or row.get("totalVolume"))
        market_cap = _as_number(row.get("marketCap") or row.get("capitalization"))

        return {
            "name": row.get("name") or row.get("companyName"),
            "exchange": row.get("exchange"),
            "current_price": current_price,
            "change": change,
            "change_percent": change_percent,
            "volume": volume,
            "market_cap": market_cap,
            "liquidity": {
                "total_value": _as_number(row.get("totalValue") or row.get("value")),
                "active_buy_volume": _as_number(row.get("activeBuyVolume")),
                "deal_volume": _as_number(row.get("dealVolume")),
            },
            "market_time": _to_datetime(row.get("date") or row.get("time")).isoformat()
            if _to_datetime(row.get("date") or row.get("time"))
            else None,
            "trading_statistics": {
                "reference_price": _as_number(row.get("basic") or row.get("referencePrice")),
                "high": _as_number(row.get("high")),
                "low": _as_number(row.get("low")),
                "open": _as_number(row.get("open")),
            },
        }

    def get_realtime_quote(self, symbol: str) -> tuple[dict[str, Any] | None, str | None]:
        try:
            return self._wait_for_price_update(symbol), None
        except FireAntError as exc:
            return None, str(exc)

    def get_trades(self, symbol: str) -> tuple[list[dict[str, Any]], str | None]:
        try:
            raw_trades = self._signalr_invoke("SubscribeTrades", [symbol])
            return self._normalize_trades(raw_trades), None
        except FireAntError as exc:
            return [], str(exc)

    def get_intraday_bars(self, symbol: str) -> tuple[list[dict[str, Any]], str | None]:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=2)

        try:
            payload = self._signalr_invoke(
                "GetBars",
                [symbol, "1", int(start.timestamp()), int(now.timestamp())],
            )
            return self._normalize_bars(payload), None
        except FireAntError as exc:
            return [], str(exc)

    def _rest_get(self, path: str) -> Any:
        if not self.token:
            raise FireAntConfigurationError(
                "Missing FIREANT_TOKEN for FireAnt REST API"
            )

        try:
            response = self.session.get(
                f"{self.rest_base_url}/{path.lstrip('/')}",
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise FireAntUnavailableError(f"Cannot connect to FireAnt: {exc}") from exc

        if response.status_code == 401:
            raise FireAntConfigurationError("FIREANT_TOKEN is invalid or expired")

        if response.status_code == 404:
            raise FireAntNotFoundError("FireAnt resource not found")

        if response.status_code >= 400:
            raise FireAntUnavailableError(
                f"FireAnt REST request failed with status {response.status_code}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise FireAntUnavailableError("FireAnt returned invalid JSON") from exc

    def _signalr_invoke(self, target: str, arguments: list[Any]) -> Any:
        if not self.token:
            raise FireAntConfigurationError(
                "Missing FIREANT_TOKEN for FireAnt quote hub"
            )

        try:
            import websocket
        except ImportError as exc:
            raise FireAntConfigurationError(
                "Missing websocket-client package for FireAnt quote hub"
            ) from exc

        websocket_url = self.quote_hub_url.replace("https://", "wss://").replace(
            "http://", "ws://"
        )
        websocket_url = f"{websocket_url}?access_token={quote(self.token)}"
        headers = [f"Authorization: Bearer {self.token}"]

        try:
            ws = websocket.create_connection(
                websocket_url,
                header=headers,
                timeout=self.timeout,
            )
        except Exception as exc:
            raise FireAntUnavailableError(f"Cannot connect to FireAnt quote hub: {exc}") from exc

        try:
            ws.send(json.dumps({"protocol": "json", "version": 1}) + SIGNALR_SEPARATOR)
            self._read_signalr_messages(ws, wait_for_handshake=True)
            ws.send(
                json.dumps(
                    {
                        "type": 1,
                        "invocationId": "1",
                        "target": target,
                        "arguments": arguments,
                    }
                )
                + SIGNALR_SEPARATOR
            )

            deadline = time.time() + self.timeout

            while time.time() < deadline:
                for message in self._read_signalr_messages(ws):
                    if message.get("type") == 3 and message.get("invocationId") == "1":
                        if message.get("error"):
                            raise FireAntUnavailableError(message["error"])

                        return message.get("result")

            raise FireAntUnavailableError(f"FireAnt quote hub timed out on {target}")
        finally:
            ws.close()

    def _wait_for_price_update(self, symbol: str) -> dict[str, Any]:
        if not self.token:
            raise FireAntConfigurationError(
                "Missing FIREANT_TOKEN for FireAnt realtime prices"
            )

        try:
            import websocket
        except ImportError as exc:
            raise FireAntConfigurationError(
                "Missing websocket-client package for FireAnt realtime prices"
            ) from exc

        websocket_url = self.quote_hub_url.replace("https://", "wss://").replace(
            "http://", "ws://"
        )
        websocket_url = f"{websocket_url}?access_token={quote(self.token)}"
        headers = [f"Authorization: Bearer {self.token}"]

        try:
            ws = websocket.create_connection(
                websocket_url,
                header=headers,
                timeout=self.timeout,
            )
        except Exception as exc:
            raise FireAntUnavailableError(f"Cannot connect to FireAnt quote hub: {exc}") from exc

        try:
            ws.send(json.dumps({"protocol": "json", "version": 1}) + SIGNALR_SEPARATOR)
            self._read_signalr_messages(ws, wait_for_handshake=True)
            deadline = time.time() + self.timeout

            while time.time() < deadline:
                for message in self._read_signalr_messages(ws):
                    if message.get("type") != 1:
                        continue

                    if message.get("target") != "UpdateLastPrices":
                        continue

                    for quote_item in self._normalize_price_updates(message.get("arguments")):
                        if quote_item.get("symbol") == symbol:
                            return quote_item

            raise FireAntUnavailableError(f"No realtime FireAnt price for {symbol}")
        finally:
            ws.close()

    def _read_signalr_messages(self, ws: Any, wait_for_handshake: bool = False) -> list[dict]:
        raw = ws.recv()
        messages = []

        for chunk in str(raw).split(SIGNALR_SEPARATOR):
            if not chunk:
                continue

            if wait_for_handshake and chunk == "{}":
                continue

            try:
                decoded = json.loads(chunk)
            except json.JSONDecodeError:
                continue

            if decoded:
                messages.append(decoded)

        return messages

    def _normalize_price_updates(self, arguments: Any) -> list[dict[str, Any]]:
        if not arguments:
            return []

        rows = arguments[0] if isinstance(arguments, list) and arguments else arguments
        result = []

        for row in rows or []:
            if not isinstance(row, list) or len(row) < 7:
                continue

            date = _to_datetime(row[1])
            result.append(
                {
                    "symbol": row[0],
                    "date": date,
                    "last": _as_number(row[2]),
                    "volume": _as_number(row[3]),
                    "totalVolume": _as_number(row[4]),
                    "totalValue": _as_number(row[5]),
                    "current": row[6],
                    "activeBuyVolume": _as_number(row[7]) if len(row) > 7 else None,
                    "dealVolume": _as_number(row[8]) if len(row) > 8 else None,
                    "volume24h": _as_number(row[9]) if len(row) > 9 else None,
                }
            )

        return result

    def _normalize_trades(self, payload: Any) -> list[dict[str, Any]]:
        rows = payload if isinstance(payload, list) else []
        normalized = []

        for row in rows[-50:]:
            if isinstance(row, dict):
                normalized.append(row)
                continue

            if isinstance(row, list):
                normalized.append(
                    {
                        "time": _to_datetime(row[0]).isoformat() if row else None,
                        "price": _as_number(row[1]) if len(row) > 1 else None,
                        "volume": _as_number(row[2]) if len(row) > 2 else None,
                        "side": row[3] if len(row) > 3 else None,
                        "raw": row,
                    }
                )

        return normalized

    def _normalize_bars(self, payload: Any) -> list[dict[str, Any]]:
        rows = payload.get("bars") if isinstance(payload, dict) else None

        if rows is None and isinstance(payload, list) and payload:
            rows = payload[0]

        bars = []

        for row in rows or []:
            if isinstance(row, dict):
                bars.append(row)
                continue

            if not isinstance(row, list) or len(row) < 6:
                continue

            date = _to_datetime(row[0])
            bars.append(
                {
                    "time": date.isoformat() if date else None,
                    "open": _as_number(row[1]),
                    "high": _as_number(row[2]),
                    "low": _as_number(row[3]),
                    "close": _as_number(row[4]),
                    "volume": _as_number(row[5]),
                    "totalVolume": _as_number(row[6]) if len(row) > 6 else None,
                    "value": _as_number(row[7]) if len(row) > 7 else None,
                    "totalValue": _as_number(row[8]) if len(row) > 8 else None,
                }
            )

        return bars

    def _market_time(self, quote: dict[str, Any] | None, latest_bar: dict[str, Any]) -> str | None:
        quote_date = _to_datetime((quote or {}).get("date"))

        if quote_date:
            return quote_date.isoformat()

        bar_time = latest_bar.get("time")
        return bar_time if isinstance(bar_time, str) else None


def get_vietnam_stock_data(symbol: str) -> dict[str, Any]:
    return FireAntProvider().get_vietnam_stock_data(symbol)
