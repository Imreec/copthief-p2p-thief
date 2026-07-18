"""Symmetric peer loop (M2 F1/F2): both peers run the SAME loop over queue transports.

This is the reference's runtime shape — no initiator, thief moves first, audits
exchanged as pushes — proven in-process so keyless CI holds the whole convention.
"""

import threading
from dataclasses import replace
from pathlib import Path

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.p2p import PeerGameResult, run_peer_game, validate_opponent_audit
from copthief_core.peer.session import PeerSession
from copthief_core.peer.transport import queue_pair
from copthief_core.shared.config import load_all

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
# The probed seed outcomes hold for the M1 random walk - pin both brain classes so the
# convention test never depends on the repo's shipped [strategy] (PR #29 rule).
PINNED = replace(PRIVATE, police_class="random", thief_class="random")


def _run_pair() -> dict[str, PeerGameResult]:
    police = PeerSession(CONSTITUTION, PINNED, role="police", seed=1)  # (1,2): survival
    thief = PeerSession(CONSTITUTION, PINNED, role="thief", seed=2)
    police_t, thief_t = queue_pair(wait_timeout=PRIVATE.connect_timeout_seconds)
    results: dict[str, PeerGameResult] = {}

    def play(session: PeerSession, transport) -> None:  # noqa: ANN001 - Protocol param
        results[session.role] = run_peer_game(
            session,
            transport,
            turn_timeout=PRIVATE.turn_timeout_seconds,
            poll_interval=PRIVATE.poll_interval_seconds,
        )

    threads = [
        threading.Thread(target=play, args=(police, police_t), name="police"),
        threading.Thread(target=play, args=(thief, thief_t), name="thief"),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=PRIVATE.turn_timeout_seconds)
    return results


def test_both_symmetric_loops_finish_with_mutual_audit_ok() -> None:
    results = _run_pair()
    threshold = CONSTITUTION.movement.survival_threshold
    assert results["thief"].outcome == "thief_survival"
    assert results["police"].outcome == "thief_survival"
    assert results["thief"].steps == threshold
    assert results["police"].steps == threshold - 1  # ends on the inbound win claim
    assert results["police"].audit_ok
    assert results["thief"].audit_ok
    assert results["police"].problems == ()
    assert results["thief"].problems == ()
    assert results["police"].game_uid == results["thief"].game_uid != ""
    assert results["police"].opponent_claim == "survival"


def test_silent_opponent_times_out_to_technical_loss_without_audit() -> None:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=11)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=22)
    police_t, thief_t = queue_pair(wait_timeout=0.05)
    # Thief only negotiates, then goes silent: police must not wait forever.
    thief_t.exchange_agreement(thief.negotiate_payload())
    result = run_peer_game(police, police_t, turn_timeout=0.1, poll_interval=0.02)
    assert result.outcome == "timeout"
    assert police.machine.state is GameState.TECHNICAL_LOSS
    assert not result.audit_ok
    assert any("audit skipped" in p for p in result.problems)


def test_survival_claim_without_enough_revealed_steps_is_flagged() -> None:
    # Derived-never-declared backstop: a "survival" result claim must be backed by
    # revealed steps reaching the threshold, or the audit is flagged.
    from copthief_core.peer.audit_flow import build_audit
    from copthief_core.peer.sealing import seal_turn

    records = [
        seal_turn(
            step=1,
            grid_size=CONSTITUTION.board.grid_size,
            position=(1, 1),
            barriers=frozenset(),
            move="STAY",
            intent="truth",
            hint="hiding",
        )
    ]
    raw = build_audit("thief", records, "survival")
    claim, problems = validate_opponent_audit(
        raw, survival_threshold=CONSTITUTION.movement.survival_threshold
    )
    assert claim == "survival"
    assert any("threshold" in p for p in problems)
