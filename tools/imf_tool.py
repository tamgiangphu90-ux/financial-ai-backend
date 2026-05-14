import asyncio
from typing import Any

import requests

from tools.source_tool import ToolResult
from utils.config import get_settings


class ImfTool:
    source_name = "IMF"

    async def fetch(self, **_: Any) -> ToolResult:
        settings = get_settings()
        url = "https://www.imf.org/external/datamapper/api/indicators"

        try:
            response = await asyncio.to_thread(
                requests.get,
                url,
                timeout=settings.request_timeout,
            )
        except requests.RequestException as exc:
            return ToolResult(source=self.source_name, status="unavailable", warning=str(exc))

        if response.status_code >= 400:
            return ToolResult(
                source=self.source_name,
                status="unavailable",
                warning=f"IMF request failed with status {response.status_code}",
            )

        try:
            payload = response.json()
        except ValueError:
            return ToolResult(source=self.source_name, status="unavailable", warning="IMF returned invalid JSON")

        return ToolResult(source=self.source_name, status="active", data=payload)
