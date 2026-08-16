"""The frame validity check wired into the session (PRD_scent §10; M7-23).

Role-blind: whichever side receives a grid validates it. The check gates on "a
non-empty grid arrived" — NOT on the model's `transmitted` flag — because the sender
transmits unconditionally (`peer/turns.py` mirrors the reference's unconditional
send() path), so under a book-v1 lock grids are on the wire and belief consumes
them even though `known_field` ignores them (probed 2026-07-28, this build's
trigger). Refusal is evidence-grade only: the whole frame is withheld from belief
and known_field, the game advances normally, and no result ever changes (SQ3).
"""

from dataclasses import replace
from pathlib import Path

from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all
from copthief_core.shared.config_model import PrivateSettings

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


def _pair(private: PrivateSettings) -> tuple[PeerSession, PeerSession]:
    police = PeerSession(CONSTITUTION, private, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, private, role="thief", seed=2)
    thief.handle_negotiate(police.negotiate_payload())
    police.handle_negotiate(thief.negotiate_payload())
    return police, thief


def _far_phantom(sender: PeerSession) -> str:
    """A cell no deposit window near the sender can reach for several turns."""
    origin = CONSTITUTION.board.axis_start_index
    last = origin + CONSTITUTION.board.grid_size - 1
    row, col = sender.position
    corner = max(
        [(origin, origin), (origin, last), (last, origin), (last, last)],
        key=lambda c: max(abs(c[0] - row), abs(c[1] - col)),
    )
    distance = max(abs(corner[0] - row), abs(corner[1] - col))
    # A fresh window reaches Chebyshev 2, so an unvisited cell at >= 3 can never
    # legitimately read 0.5 (on a 7x7 board the farthest corner is always >= 3).
    assert distance >= 3, "fixture assumption: a corner beyond the deposit window"
    return f"{corner[0]},{corner[1]}"


def _forged(sender: PeerSession, message: dict) -> dict:
    """The honest outbound message with one phantom cell no emitter can explain."""
    message["smell_grid"] = {**message["smell_grid"], _far_phantom(sender): 0.5}
    return message


def test_honest_round_trips_record_no_refusals() -> None:
    police, thief = _pair(PRIVATE)
    for turn in range(3):
        police.handle_receive_turn(thief.take_turn(now=float(turn)))
        thief.handle_receive_turn(police.take_turn(now=float(turn) + 0.5))
    assert police.scent_refusals == []
    assert thief.scent_refusals == []


def test_forged_frame_is_refused_whole() -> None:
    police, thief = _pair(PRIVATE)
    message = _forged(thief, thief.take_turn(now=1.0))
    ack = police.handle_receive_turn(message)
    assert ack["status"] == "ok"  # the wire ack is unchanged — refusal is log-only
    assert police.scent_refusals == [{"step": 1, "cells": len(message["smell_grid"])}]
    assert police.known_field.cells() == {}  # nothing absorbed


def test_refused_grid_never_reaches_belief_with_quarantine_off() -> None:
    # M13 (ADR-0016): the live config arms refused_frame_trust > 0 (quarantine tier,
    # pinned in test_frame_quarantine.py); THIS pin holds the 0.0 posture byte-true.
    quarantine_off = replace(PRIVATE, refused_frame_trust=0.0)
    police, thief = _pair(quarantine_off)
    message = _forged(thief, thief.take_turn(now=1.0))
    police.handle_receive_turn(message)
    # Control twin (same seeds, same underlying turn): the grid simply absent.
    police2, thief2 = _pair(quarantine_off)
    control = thief2.take_turn(now=1.0)
    control["smell_grid"] = {}
    police2.handle_receive_turn(control)
    assert police.belief.probs() == police2.belief.probs()


def test_game_continues_and_the_check_recovers_after_a_refusal() -> None:
    police, thief = _pair(PRIVATE)
    police.handle_receive_turn(_forged(thief, thief.take_turn(now=1.0)))
    thief.handle_receive_turn(police.take_turn(now=1.5))
    police.handle_receive_turn(thief.take_turn(now=2.0))  # honest, vs the forged base
    thief.handle_receive_turn(police.take_turn(now=2.5))
    police.handle_receive_turn(thief.take_turn(now=3.0))  # honest vs honest again
    refused_steps = [entry["step"] for entry in police.scent_refusals]
    assert 1 in refused_steps  # the forged frame itself
    # A refused frame still serves as the next baseline (self-healing): whatever
    # happened at step 2, two honest consecutive frames accept again by step 3.
    assert 3 not in refused_steps
    assert thief.scent_refusals == []  # our own outbound frames stayed honest


def test_caught_final_is_never_refused_even_as_a_zero_step_resend() -> None:
    """Round-17 pin (the opponent team's finding in their OWN receiver, verified absent
    in ours): a game-ending caught=true final whose grid is a ZERO-STEP re-send of the
    previous field can never satisfy the one-advance law — and must never be asked to.
    The `final_caught` exemption has skipped it since the first build (PRD §10.2); this
    pin keeps a capture ending from ever seeding a false refusal into rule-36 evidence.
    Both concede shapes covered: an advancing final (ours) and an unchanged re-send
    (theirs)."""
    for zero_step_resend in (False, True):
        police, thief = _pair(PRIVATE)
        first = thief.take_turn(now=1.0)
        police.handle_receive_turn(first)
        claim_turn = police.take_turn(now=1.5)
        claim_turn["capture_claim"] = list(thief.position)  # the claim lands
        thief.handle_receive_turn(claim_turn)
        final = thief.take_turn(now=2.0)
        assert final["claim_response"] == {"claim": claim_turn["capture_claim"], "caught": True}
        if zero_step_resend:
            final["smell_grid"] = dict(first["smell_grid"])  # their concede shape
        police.handle_receive_turn(final)
        assert police.scent_refusals == []


def test_empty_grid_is_absence_of_data_never_impossible_data() -> None:
    """Round-16 pin (the opponent team's option-3 trap, which their checker had and
    ours must never grow): a peer transmitting `{}` — the legal form of a
    not-transmitted arrangement — is absence of data, not a physics violation. The
    gate skips entirely: no refusal, nothing absorbed, the game advances."""
    police, thief = _pair(PRIVATE)
    for turn in range(3):
        message = thief.take_turn(now=float(turn))
        message["smell_grid"] = {}
        ack = police.handle_receive_turn(message)
        assert ack["status"] == "ok"
        reply = police.take_turn(now=float(turn) + 0.5)
        thief.handle_receive_turn(reply)
    assert police.scent_refusals == []  # never refused, never latched
    assert police.known_field.cells() == {}


def test_disabled_gate_absorbs_even_a_forged_frame() -> None:
    police, thief = _pair(replace(PRIVATE, frame_check=False))
    police.handle_receive_turn(_forged(thief, thief.take_turn(now=1.0)))
    assert police.scent_refusals == []
    assert police.known_field.cells() != {}  # absorbed, exactly the pre-M7-23 behavior


def test_refusal_event_emitted_only_for_the_just_accepted_step() -> None:
    """The loop's JSONL surface (§10.2): loud for a refused frame, silent otherwise —
    refusals must reach the log the mutual audit reads, not only a console."""
    from copthief_core.peer import events

    police, thief = _pair(PRIVATE)
    message = _forged(thief, thief.take_turn(now=1.0))
    ack = police.handle_receive_turn(message)
    sink: list[dict] = []
    events.scent_refusal(sink.append, police, ack["step"])
    assert sink == [
        {
            "event": "scent_frame_refused",
            "receiver": police.role,
            "payload": {"step": 1, "cells": len(message["smell_grid"])},
        }
    ]
    events.scent_refusal(sink.append, thief, 1)  # no refusals recorded -> silent
    events.scent_refusal(sink.append, police, 2)  # stale step -> silent
    assert len(sink) == 1


def test_bookv1_transmitted_frames_are_checked_too() -> None:
    """The counted physics is NOT exempt: the sender transmits unconditionally and
    belief reads the grid (the 2026-07-28 probe), so the gate follows the ARRIVING
    grid, never the model's `transmitted` flag."""
    private = replace(PRIVATE, scent_model="multiplicative_book_v1")
    police, thief = _pair(private)
    for turn in range(2):  # honest book-v1 traffic passes (false-positive property)
        police.handle_receive_turn(thief.take_turn(now=float(turn)))
        thief.handle_receive_turn(police.take_turn(now=float(turn) + 0.5))
    assert police.scent_refusals == []
    message = _forged(thief, thief.take_turn(now=3.0))
    police.handle_receive_turn(message)
    assert [entry["step"] for entry in police.scent_refusals] == [3]
