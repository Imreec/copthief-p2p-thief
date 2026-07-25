"""M7-11b: a bystander's agreement must not kill our handshake.

Against a role-split opponent (two runners, each owning one role's windows —
Alon's committed shape), their NEXT window's peer starts early and re-pushes its
agreement at our single port while our current window is still handshaking. That
agreement carries the identical signed terms and a valid signature over its own
nonce — it fails ONLY the pairing check (wrong index, or our own role). The
full-dress M7-11 rig observed the then-current behavior: the pairing refusal
raised out of `run_peer_game`, the peer DIED, and every window where we moved
second collapsed in cascade. A bystander belongs to a different game; refusing
it must leave us waiting for our real counterpart.
"""

from __future__ import annotations

import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from copthief_core.peer.p2p import run_peer_game
from copthief_core.peer.session import NegotiationError, PeerSession
from copthief_core.peer.transport import queue_pair
from copthief_core.shared.config import load_all

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)
PRIVATE = replace(_SHIPPED, police_class="random", thief_class="random")


def _bystander_agreement(*, role: str, sub_game_number: int) -> dict[str, Any]:
    """A REAL agreement from another window: identical signed terms, its own valid
    nonce and signature — wrong only in WHICH game it belongs to."""
    bystander = PeerSession(
        CONSTITUTION,
        replace(PRIVATE, sub_game_number=sub_game_number),
        role=role,
        seed=99,
    )
    return bystander.negotiate_payload()


def test_a_bystanders_agreement_is_refused_and_the_real_game_still_plays() -> None:
    """The rig's s1: our thief (sub-game 1) gets the opponent's OTHER runner's
    agreement (equal role, next index) BEFORE its true counterpart's."""
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief_transport, police_transport = queue_pair(wait_timeout=2.0)
    thief_transport._own.agreements.put(  # noqa: SLF001 - inject ahead of the counterpart
        _bystander_agreement(role="thief", sub_game_number=2)
    )
    events: list[dict[str, Any]] = []

    counterpart_result: list[Any] = []

    def counterpart() -> None:
        counterpart_result.append(
            run_peer_game(police, police_transport, turn_timeout=5.0, poll_interval=0.05)
        )

    runner = threading.Thread(target=counterpart, name="true-counterpart")
    runner.start()
    result = run_peer_game(
        thief, thief_transport, turn_timeout=5.0, poll_interval=0.05, log=events.append
    )
    runner.join(timeout=10)

    kinds = [e.get("event") for e in events]
    assert "agreement_refused" in kinds, "the bystander must be refused ON THE RECORD"
    assert kinds.index("agreement_refused") < kinds.index("negotiated")
    assert result.audit_ok is True  # the REAL game played to a clean mutual audit
    assert counterpart_result, "the counterpart must have finished its game"
    assert counterpart_result[0].audit_ok is True
    reasons = [e["payload"]["reason"] for e in events if e.get("event") == "agreement_refused"]
    assert any("sub-game" in r or "role" in r for r in reasons)


def test_a_bystander_storm_without_a_counterpart_still_ends_refused() -> None:
    """Tolerance must stay bounded: if only bystanders ever arrive, the handshake
    ends in the same loud NegotiationError as silence — never a hang, never a crash
    with a raw pairing refusal."""
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    thief_transport, _police_transport = queue_pair(wait_timeout=0.1)
    for _ in range(2):
        thief_transport._own.agreements.put(  # noqa: SLF001 - nobody else is coming
            _bystander_agreement(role="thief", sub_game_number=2)
        )
    started = time.monotonic()
    with pytest.raises(NegotiationError):
        run_peer_game(thief, thief_transport, turn_timeout=0.5, poll_interval=0.05)
    assert time.monotonic() - started < 5.0  # bounded by the budgets, not a hang


def test_handle_negotiate_still_refuses_a_mispairing_directly() -> None:
    """The refusal itself is unchanged — a mispaired agreement never negotiates; the
    tolerance lives in the LOOP, not in the gate."""
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    with pytest.raises(NegotiationError, match="sub-game|role"):
        thief.handle_negotiate(_bystander_agreement(role="thief", sub_game_number=2))
