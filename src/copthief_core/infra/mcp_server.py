"""Real FastMCP server adapter (PLAN §2): each peer's own public mailbox.

M2 F1 (oracle sha 960499fd): the reference never composes replies into tool responses —
every tool ENQUEUES the inbound payload into this peer's thread-safe inboxes and returns
a bare ack; the peer loop (peer/p2p) drains them. Thin by design: no game logic here.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from copthief_core.peer.transport import PeerQueues


def build_server(role: str, inboxes: PeerQueues) -> FastMCP:
    """A FastMCP server exposing the wire contract's four push-tools for one peer."""
    mcp = FastMCP(name=f"copthief-{role}")

    @mcp.tool
    def negotiate(message: dict[str, Any]) -> dict[str, Any]:
        """Receive the opponent's signed game agreement."""
        inboxes.put("agreements", message)
        return {"ok": True}

    @mcp.tool
    def receive_turn(message: dict[str, Any]) -> dict[str, Any]:
        """Receive the opponent's turn message (the turn token travels with it)."""
        inboxes.put("turns", message)
        return {"ok": True}

    @mcp.tool
    def submit_audit(payload: dict[str, Any]) -> dict[str, Any]:
        """Receive the opponent's end-of-game audit reveal (records + nonces)."""
        inboxes.put("audits", payload)
        return {"ok": True}

    @mcp.tool
    def receive_control(message: dict[str, Any]) -> dict[str, Any]:
        """Receive an opponent control signal (opt-in channel; never sealed)."""
        inboxes.put("controls", message)
        return {"ok": True}

    return mcp


def start_server(role: str, inboxes: PeerQueues, *, host: str, port: int) -> None:
    """Serve this peer's inbox tools on a daemon thread (returns once started)."""
    import threading

    server = build_server(role, inboxes)
    thread = threading.Thread(
        # log_level="warning" keeps stdout clean: INFO access logs once filled a
        # subprocess pipe buffer and froze the peer mid-game (M2 debugging).
        target=lambda: server.run(
            transport="http", host=host, port=port, show_banner=False, log_level="warning"
        ),
        daemon=True,
        name=f"mcp-{role}",
    )
    thread.start()
