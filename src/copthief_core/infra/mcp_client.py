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
    """Outbound tool calls to one peer's MCP endpoint URL (host/port are config-owned).

    `timeout` is MANDATORY and has no default (M7-57). Passing none leaves the deadline
    to the MCP SDK, and a deadline nobody chose is one nobody has reconciled against the
    SIGNED `response_timeout_sec` the opponent enforces — which is how a delivered-but-
    unanswered push cost us 61 s inside a 30 s rule budget in the 2026-08-09 friendly.
    """

    def __init__(self, url: str, *, timeout: float) -> None:
        self._url = url
        self._timeout = timeout

    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Deliver one tool call synchronously; the result must be an object."""
        return asyncio.run(self._call(tool, payload))

    async def _call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        # The budget is TOTAL — enter, tool call, and session close. `Client(timeout=)`
        # alone bounds only the tool call: on 2026-08-19 (ali-ahm1 friendly) a push was
        # served in 95.6 ms and the client then hung ~61 s CLOSING the session, so our
        # next turn left one second after the opponent's signed 60 s window. Same
        # disease as M7-57's original 2026-08-09 face, one layer down.
        return await asyncio.wait_for(self._exchange(tool, payload), timeout=self._timeout)

    async def _exchange(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with Client(self._url, timeout=self._timeout) as client:
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
        await asyncio.wait_for(self._ping_exchange(), timeout=self._timeout)

    async def _ping_exchange(self) -> None:
        async with Client(self._url, timeout=self._timeout) as client:
            await client.list_tools()
