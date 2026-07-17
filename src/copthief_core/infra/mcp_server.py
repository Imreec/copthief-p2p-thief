"""Real FastMCP server adapter (PLAN §2): the four tools, bound to one PeerSession.

Thin by design — all logic lives in peer/*; this file only exposes it over MCP.
M1 composition note (M2-verified against the reference): the localhost skeleton is
driven by the initiator, so `negotiate` returns the responder's own negotiate payload
under "peer", and `receive_turn` returns the responder's next TurnMessage under "turn"
— response-carried instead of a symmetric back-call. The reference's actual calling
convention gets pinned at the M2 oracle spike and this adapter adapts, not the peer.
"""

from __future__ import annotations

import time
from typing import Any

from fastmcp import FastMCP

from copthief_core.peer.audit_flow import handle_submit_audit
from copthief_core.peer.session import PeerSession


def build_server(session: PeerSession) -> FastMCP:
    """A FastMCP server exposing the wire contract's four tools for `session`."""
    mcp = FastMCP(name=f"copthief-{session.role}")

    @mcp.tool
    def negotiate(message: dict[str, Any]) -> dict[str, Any]:
        """Pre-game gate; the ack carries our own negotiate payload back (M1 composition)."""
        ack = session.handle_negotiate(message)
        return {**ack, "peer": session.negotiate_payload()}

    @mcp.tool
    def receive_turn(message: dict[str, Any]) -> dict[str, Any]:
        """Accept the opponent's turn; reply with ours while we are the one behind."""
        ack = session.handle_receive_turn(message)
        if not session.machine.is_terminal and len(session.records) < len(session.inbound):
            ack["turn"] = session.take_turn(now=time.time())
        return ack

    @mcp.tool
    def submit_audit(payload: dict[str, Any]) -> dict[str, Any]:
        """End-of-game audit: verify theirs, answer with ours (one round trip)."""
        return handle_submit_audit(session, payload)

    @mcp.tool
    def receive_control(message: dict[str, Any]) -> dict[str, Any]:
        """Opt-in status side channel — never sealed."""
        return session.handle_receive_control(message)

    return mcp


def serve(session: PeerSession, *, host: str, port: int) -> None:
    """Blocking HTTP serve of the session's tools (Input: bind address; runs forever)."""
    build_server(session).run(transport="http", host=host, port=port, show_banner=False)
