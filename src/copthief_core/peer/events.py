"""Log schema v1.1 event builders (PRD_gui_replay §3, workstream L).

One event stream serves every consumer — the JSONL archive now, the live GUI queue at
M4-2 — so anything a view renders is by definition something the log witnessed. Inbound
structures are archived VERBATIM at the loop seam, *before* validation: FastMCP hands us
a parsed dict (pre-parse wire bytes never reach this layer), and archiving that dict
losslessly under the canonical dumps is sufficient to re-derive every hash, because
commits are computed over canonical dict serialization (kit CORE). Log-only: nothing
here touches the wire format (constraint #13 untriggered).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from copthief_core.domain.state_machine import GameState

if TYPE_CHECKING:  # annotation-only: p2p imports THIS module at runtime
    from copthief_core.peer.session import PeerSession

LogFn = Callable[[dict[str, Any]], None]


def wire_observability(session: PeerSession, emit: LogFn) -> None:
    """Attach the transition stream to a session's state machine (Input: the session +
    the game's event sink; Output: none — `advance` now reports every legal hop)."""

    def on_advance(old: GameState, new: GameState, trigger: str) -> None:
        emit(
            {
                "event": "transition",
                "sender": session.role,
                "payload": {"from": old.value, "to": new.value, "trigger": trigger},
            }
        )

    session.machine.observer = on_advance


def inbound(emit: LogFn, kind: str, receiver: str, raw: dict[str, Any]) -> None:
    """Archive one inbound dict verbatim, pre-validation (dispute-grade evidence)."""
    emit({"event": kind, "receiver": receiver, "raw": raw})


def tolerated(emit: LogFn, session: PeerSession, disposition: str, step: int) -> None:
    """One inbound message the transport layer absorbed (M7-8: a redelivery or an
    early arrival). Logged loudly on purpose — a warm-up drill has to be able to SHOW
    that the duplicates arrived and that none of them advanced the game."""
    emit(
        {
            "event": "inbound_tolerated",
            "receiver": session.role,
            "payload": {"disposition": disposition, "step": step},
        }
    )


def belief_snapshot(emit: LogFn, session: PeerSession) -> None:
    """One post-update belief snapshot (Input: session after its inbound pipeline ran;
    Output: none — the `belief` event feeds the M4-2 heatmap and the M4-4 overlay)."""
    argmax = session.belief.argmax()
    emit(
        {
            "event": "belief",
            "sender": session.role,
            "payload": {
                "step": len(session.inbound),
                "grid": {f"{r},{c}": p for (r, c), p in sorted(session.belief.probs().items())},
                "argmax": f"{argmax[0]},{argmax[1]}",
            },
        }
    )


def scent_refusal(emit: LogFn, session: PeerSession, step: int) -> None:
    """The just-accepted message's grid failed the frame validity check (M7-23) —
    loud JSONL so refusals surface at the mutual audit, never only a console.
    Silent unless the LATEST refusal is exactly `step`: the check refuses at most
    once per accepted message, so anything else is a stale entry already reported."""
    if session.scent_refusals and session.scent_refusals[-1]["step"] == step:
        emit(
            {
                "event": "scent_frame_refused",
                "receiver": session.role,
                "payload": dict(session.scent_refusals[-1]),
            }
        )


def decision(emit: LogFn, session: PeerSession) -> None:
    """Provenance of the just-sealed turn (PLAN §7 'decisions + provenance')."""
    record = session.records[-1].payload
    emit(
        {
            "event": "decision",
            "sender": session.role,
            "payload": {
                "step": record["step"],
                "brain": type(session.brain).__name__,
                "move": record["move"],
                "intent": record["intent"],
            },
        }
    )
