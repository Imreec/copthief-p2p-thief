"""M7-57: every outbound tool call carries an explicit deadline.

The live defect (best2934 friendly, 2026-08-09, both sub-games): `McpToolClient` passed
no timeout to the FastMCP client, so each call inherited the MCP SDK's own default. A
push that was DELIVERED but never answered therefore blocked for that hidden default,
and `_push_with_retry` then tried again — two hidden waits plus one retry interval, and
our step-16 turn left 61.0 s after the opponent's step 15 (their clock and ours agree to
the second). Their rule deadline is the SIGNED `response_timeout_sec`, so the game was
already lost while we sat inside a timeout nobody had chosen.

The budget an opponent enforces is signed and shared; the budget we wait for was neither
chosen nor visible. This pins that it is now ours, explicit, and asserted against theirs.
"""

from __future__ import annotations

from typing import Any

import pytest

from copthief_core.infra import mcp_client as mcp_client_module
from copthief_core.infra.mcp_client import McpToolClient


class _FakeResult:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data


class _RecordingClient:
    """Stands in for `fastmcp.Client`, recording the kwargs it was constructed with."""

    seen: list[dict[str, Any]] = []

    def __init__(self, url: str, *, timeout: float) -> None:
        self.url = url
        type(self).seen.append({"timeout": timeout})

    async def __aenter__(self) -> _RecordingClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def call_tool(self, _tool: str, _args: dict[str, Any]) -> _FakeResult:
        return _FakeResult({"ok": True})

    async def list_tools(self) -> list[str]:
        return []


@pytest.fixture(autouse=True)
def _recording(monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingClient.seen = []
    monkeypatch.setattr(mcp_client_module, "Client", _RecordingClient)


def test_call_passes_the_configured_timeout() -> None:
    """A tool call must not inherit a deadline nobody chose."""
    McpToolClient("http://peer.invalid/mcp", timeout=10.0).call("receive_turn", {"step": 1})
    assert _RecordingClient.seen == [{"timeout": 10.0}]


def test_readiness_ping_carries_the_same_deadline() -> None:
    """The pre-game ping is the same transport and gets the same budget."""
    McpToolClient("http://peer.invalid/mcp", timeout=7.5).wait_ready(attempts=1, delay_sec=0.0)
    assert _RecordingClient.seen == [{"timeout": 7.5}]


def test_timeout_is_required() -> None:
    """No default: an unchosen deadline is the defect this module exists to prevent."""
    with pytest.raises(TypeError):
        McpToolClient("http://peer.invalid/mcp")  # type: ignore[call-arg]
