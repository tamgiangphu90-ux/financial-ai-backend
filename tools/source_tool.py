from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    source: str
    status: str
    data: dict[str, Any] | list[dict[str, Any]] | None = None
    warning: str | None = None


class PlaceholderSourceTool:
    source_name = "Unknown"

    async def fetch(self, *args, **kwargs) -> ToolResult:
        return ToolResult(
            source=self.source_name,
            status="placeholder",
            data=None,
            warning="Connector is registered but not enabled. Use only public pages or authorized APIs when implementing.",
        )
