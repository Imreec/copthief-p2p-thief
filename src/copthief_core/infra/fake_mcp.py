"""In-process MCP fake (PLAN §2/§12): the same tool-call surface, zero network.

A FakeMcpServer holds named tool handlers (the four peer tools); a FakeMcpClient
dispatches `call(tool, payload)` directly to them. The real FastMCP adapters (M1-7)
implement the identical calling convention, so the peer layer cannot tell transports
apart — which is exactly what makes keyless CI honest.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


class FakeMcpServer:
    """A named-tool dispatch table standing in for a FastMCP server."""

    def __init__(self, tools: dict[str, ToolHandler]) -> None:
        self._tools = dict(tools)

    def dispatch(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Invoke `tool` with `payload`; unknown tools raise KeyError (loud, like a 404)."""
        if tool not in self._tools:
            raise KeyError(f"unknown tool: {tool}")
        return self._tools[tool](payload)


class FakeMcpClient:
    """The client half: `call` mirrors the outbound MCP tool-call signature."""

    def __init__(self, server: FakeMcpServer) -> None:
        self._server = server

    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Synchronously deliver one tool call to the paired fake server."""
        return self._server.dispatch(tool, payload)
