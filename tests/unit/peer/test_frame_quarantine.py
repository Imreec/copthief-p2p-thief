"""M13 refused-frame quarantine (ADR-0016): degraded sight beats blindness.

The najamjad counted series: every one of 35/35 inbound frames failed the physics
check in all three cop games, the belief never converged (argmax 0/34 at every lag),
and the cop chased phantoms past a thief that barely moved. The refusal design
(M7-23) keeps its evidence role untouched — refusals are still recorded, the known
field still absorbs nothing — but with `[scent] refused_frame_trust > 0` the belief
may read the refused grid at scaled trust: SQ3's multiplicative floor (never
eliminate) bounds what a fabricated frame can do, and the counted evidence says
blindness costs more.
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
    """A cell no deposit window near the sender can reach (test_session_frame_check)."""
    origin = CONSTITUTION.board.axis_start_index
    last = origin + CONSTITUTION.board.grid_size - 1
    row, col = sender.position
    corner = max(
        [(origin, origin), (origin, last), (last, origin), (last, last)],
        key=lambda c: max(abs(c[0] - row), abs(c[1] - col)),
    )
    return f"{corner[0]},{corner[1]}"


def _forged(sender: PeerSession, message: dict) -> dict:
    message["smell_grid"] = {**message["smell_grid"], _far_phantom(sender): 0.5}
    return message


def test_quarantine_off_keeps_the_refused_frame_out_of_belief() -> None:
    police, thief = _pair(replace(PRIVATE, refused_frame_trust=0.0))
    police.handle_receive_turn(_forged(thief, thief.take_turn(now=1.0)))
    police2, thief2 = _pair(replace(PRIVATE, refused_frame_trust=0.0))
    control = thief2.take_turn(now=1.0)
    control["smell_grid"] = {}
    police2.handle_receive_turn(control)
    assert police.belief.probs() == police2.belief.probs()


def test_quarantine_reads_the_refused_frame_at_scaled_trust() -> None:
    police, thief = _pair(replace(PRIVATE, refused_frame_trust=0.5))
    message = _forged(thief, thief.take_turn(now=1.0))
    police.handle_receive_turn(message)
    # The refusal evidence is untouched...
    assert [entry["step"] for entry in police.scent_refusals] == [1]
    assert police.known_field.cells() == {}
    # ...but the belief moved: the blind twin (grid withheld) reads differently.
    police2, thief2 = _pair(replace(PRIVATE, refused_frame_trust=0.5))
    control = thief2.take_turn(now=1.0)
    control["smell_grid"] = {}
    police2.handle_receive_turn(control)
    assert police.belief.probs() != police2.belief.probs()


def test_quarantined_trust_moves_the_belief_less_than_full_trust() -> None:
    police_half, thief_half = _pair(replace(PRIVATE, refused_frame_trust=0.5))
    message = _forged(thief_half, thief_half.take_turn(now=1.0))
    police_half.handle_receive_turn(message)
    # Full-trust twin: same turn, gate disabled, so the same grid lands unscaled.
    police_full, thief_full = _pair(replace(PRIVATE, frame_check=False))
    police_full.handle_receive_turn(_forged(thief_full, thief_full.take_turn(now=1.0)))
    peak_full = max(police_full.belief.probs().values())
    peak_half = max(police_half.belief.probs().values())
    # Blind twin: the same turn arrives with the grid withheld (predict-only belief).
    police_blind, thief_blind = _pair(replace(PRIVATE, refused_frame_trust=0.0))
    control = thief_blind.take_turn(now=1.0)
    control["smell_grid"] = {}
    police_blind.handle_receive_turn(control)
    peak_blind = max(police_blind.belief.probs().values())
    assert peak_blind < peak_half < peak_full
