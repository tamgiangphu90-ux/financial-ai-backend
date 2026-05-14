import asyncio
import os
from typing import Any

import requests

from tools.source_tool import ToolResult
from utils.config import get_settings


class FredTool:
    source_name = "FRED"

    async def fetch(self, series_id: str = "FEDFUNDS", **_: Any) -> ToolResult:
        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            return ToolResult(
                source=self.source_name,
                status="requires_api_key",
                warning="Missing FRED_API_KEY environment variable",
            )

        settings = get_settings()
        url = "https://api.stlouisfed.org/fred/series/observations"

        try:
            response = await asyncio.to_thread(
                requests.get,
                url,
                params={
                    "series_id": series_id,
                    "api_key": api_key,
                    "file_type": "json",
                    "limit": 10,
                    "sort_order": "desc",
                },
                timeout=settings.request_timeout,
            )
        except requests.RequestException as exc:
            return ToolResult(source=self.source_name, status="unavailable", warning=str(exc))

        if response.status_code in {401, 403}:
            return ToolResult(source=self.source_name, status="requires_api_key", warning="FRED_API_KEY is invalid")
        if response.status_code >= 400:
            return ToolResult(
                source=self.source_name,
                status="unavailable",
                warning=f"FRED request failed with status {response.status_code}",
            )

        try:
            payload = response.json()
        except ValueError:
            return ToolResult(source=self.source_name, status="unavailable", warning="FRED returned invalid JSON")

        return ToolResult(
            source=self.source_name,
            status="active",
            data={"series_id": series_id, "observations": payload.get("observations", [])},
        )
