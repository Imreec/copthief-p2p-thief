"""Real FastMCP client adapter: sync tool calls against an opponent's MCP endpoint.

Presents the exact `call(tool, payload) -> dict` surface of the in-process fake, so the
peer layer cannot tell transports apart (PLAN §12). One connection per call — plenty for
the M1 localhost skeleton; pooling arrives with the reliability rail if ever needed.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastmcp import Client

# PLAN §6 fixes each tool's argument name; submit_audit is the odd one out.
_PARAM_NAME = {"submit_audit": "payload"}


class McpToolClient:
    """Outbound tool calls to one peer's MCP endpoint URL (host/port are config-owned)."""

    def __init__(self, url: str) -> None:
        self._url = url

    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Deliver one tool call synchronously; the result must be an object."""
        return asyncio.run(self._call(tool, payload))

    async def _call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with Client(self._url) as client:
            result = await client.call_tool(tool, {_PARAM_NAME.get(tool, "message"): payload})
        data = result.data
        if not isinstance(data, dict):
            raise TypeError(f"{tool}: expected an object result, got {type(data).__name__}")
        return data

    def wait_ready(self, *, attempts: int, delay_sec: float) -> None:
        """Poll the endpoint until it answers (a just-spawned peer process needs a beat)."""
        for attempt in range(attempts):
            try:
                asyncio.run(self._ping())
            except (OSError, RuntimeError, Exception):  # noqa: B014 - transport-layer soup
                if attempt == attempts - 1:
                    raise
                time.sleep(delay_sec)
            else:
                return

    async def _ping(self) -> None:
        async with Client(self._url) as client:
            await client.list_tools()
