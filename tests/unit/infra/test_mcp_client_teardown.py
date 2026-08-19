"""M7-57 second face (ali-ahm1 friendly, 2026-08-19): the deadline covers teardown too.

The live defect: `Client(timeout=...)` bounds the tool call, but NOT the session
close (`__aexit__`). Our step-19 push was served in 95.6 ms — then the client hung
~61 s closing the session (the opponent's edge shows our step-19 session's DELETE
never arrived), so our step-20 turn left one second after their signed 60 s window
expired. Self-play reproduced the family locally: a settled peer's lost ack held
`submit_audit` retries for a full minute. Both faces are one rule violated: a call
whose useful work is done may not keep spending the loop's time. `asyncio.wait_for`
around the WHOLE call — enter, tool call, exit — makes the configured budget total.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from copthief_core.infra import mcp_client as mcp_client_module
from copthief_core.infra.mcp_client import McpToolClient


class _FakeResult:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data


class _HangingExitClient:
    """Serves the tool call instantly, then hangs forever in session close."""

    def __init__(self, url: str, *, timeout: float) -> None:
        self.url = url

    async def __aenter__(self) -> _HangingExitClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        import asyncio

        await asyncio.sleep(3600)  # the 2026-08-19 hang, condensed

    async def call_tool(self, _tool: str, _args: dict[str, Any]) -> _FakeResult:
        return _FakeResult({"ok": True})

    async def list_tools(self) -> list[str]:
        return []


class _CleanClient(_HangingExitClient):
    """The healthy path: instant service, instant close."""

    async def __aexit__(self, *_exc: object) -> None:
        return None


def test_hanging_teardown_is_cut_at_the_configured_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A call whose cleanup hangs must fail within the budget, not a minute later."""
    monkeypatch.setattr(mcp_client_module, "Client", _HangingExitClient)
    client = McpToolClient("http://peer.invalid/mcp", timeout=0.2)
    started = time.perf_counter()
    with pytest.raises(TimeoutError):
        client.call("receive_turn", {"step": 20})
    assert time.perf_counter() - started < 2.0


def test_healthy_call_is_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ceiling only fires on the pathological path — clean calls behave as before."""
    monkeypatch.setattr(mcp_client_module, "Client", _CleanClient)
    client = McpToolClient("http://peer.invalid/mcp", timeout=0.2)
    assert client.call("receive_turn", {"step": 1}) == {"ok": True}


def test_readiness_ping_shares_the_total_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    """`wait_ready` is the same transport: a hanging close must not eat its budget."""
    monkeypatch.setattr(mcp_client_module, "Client", _HangingExitClient)
    client = McpToolClient("http://peer.invalid/mcp", timeout=0.2)
    started = time.perf_counter()
    with pytest.raises(TimeoutError):
        client.wait_ready(attempts=1, delay_sec=0.0)
    assert time.perf_counter() - started < 2.0
