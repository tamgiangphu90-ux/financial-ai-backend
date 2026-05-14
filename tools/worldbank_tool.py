import asyncio
from typing import Any

import requests

from tools.source_tool import ToolResult
from utils.config import get_settings


class WorldBankTool:
    source_name = "World Bank"

    async def fetch(
        self,
        country: str = "VN",
        indicator: str = "NY.GDP.MKTP.CD",
        **_: Any,
    ) -> ToolResult:
        settings = get_settings()
        url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"

        try:
            response = await asyncio.to_thread(
                requests.get,
                url,
                params={"format": "json", "per_page": 5},
                timeout=settings.request_timeout,
            )
        except requests.RequestException as exc:
            return ToolResult(source=self.source_name, status="unavailable", warning=str(exc))

        if response.status_code >= 400:
            return ToolResult(
                source=self.source_name,
                status="unavailable",
                warning=f"World Bank request failed with status {response.status_code}",
            )

        try:
            payload = response.json()
        except ValueError:
            return ToolResult(source=self.source_name, status="unavailable", warning="World Bank returned invalid JSON")

        return ToolResult(
            source=self.source_name,
            status="active",
            data={"country": country, "indicator": indicator, "observations": payload[1] if len(payload) > 1 else []},
        )
