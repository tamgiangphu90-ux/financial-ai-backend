import asyncio
from typing import Any

import requests

from tools.source_tool import ToolResult
from utils.config import get_settings


class VietstockTool:
    source_name = "Vietstock"

    async def fetch(self, path: str = "", **_: Any) -> ToolResult:
        settings = get_settings()
        url = f"https://vietstock.vn/{path.lstrip('/')}" if path else "https://vietstock.vn"

        try:
            response = await asyncio.to_thread(
                requests.get,
                url,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"},
                timeout=settings.request_timeout,
            )
        except requests.RequestException as exc:
            return ToolResult(source=self.source_name, status="unavailable", warning=str(exc))

        if response.status_code >= 400:
            return ToolResult(
                source=self.source_name,
                status="unavailable",
                warning=f"Vietstock request failed with status {response.status_code}",
            )

        return ToolResult(
            source=self.source_name,
            status="active",
            data={
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "excerpt": response.text[:500],
            },
        )
