"""SQ1 scent wiring in the session (PRD_scent §3): deposit-after-move → decay → transmit.

The mover deposits at its NEW position with the signed center intensity, the own trail
decays ONCE, and the snapshot rides the outbound TurnMessage; the receiver absorbs the
grid into its known field, then decays it once per received message (oracle sha
960499fd, spike SQ1). The reference deposits on EVERY outbound turn — STAY and the
mandatory final caught message included (its send() path is unconditional).
"""

from pathlib import Path

from copthief_core.domain.crypto import canonical_hash
from copthief_core.domain.scent import locked_model_document
from copthief_core.domain.state_machine import GameState
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)

# The PRD_scent §2 consequence for the shipped config: a just-laid center transmits
# at center_intensity - decay (values restated here as expectations only).
FRESH_CENTER = round(CONSTITUTION.pheromones.center_intensity - CONSTITUTION.pheromones.decay, 3)


def _pair() -> tuple[PeerSession, PeerSession]:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    thief.handle_negotiate(police.negotiate_payload())
    police.handle_negotiate(thief.negotiate_payload())
    return police, thief


def _fresh_centers(smell_grid: dict[str, float]) -> list[str]:
    return [key for key, value in smell_grid.items() if value == FRESH_CENTER]


def test_first_turn_transmits_the_fresh_trail_centered_on_the_new_position() -> None:
    _police, thief = _pair()
    message = thief.take_turn(now=1.0)
    grid = message["smell_grid"]
    assert grid, "outbound smell_grid must be non-empty from M3-2 on"
    row, col = thief.position
    assert grid[f"{row},{col}"] == FRESH_CENTER  # deposit AFTER the move, then one decay


def test_every_turn_has_exactly_one_fresh_center() -> None:
    police, thief = _pair()
    for turn in range(3):
        message = thief.take_turn(now=float(turn))
        assert len(_fresh_centers(message["smell_grid"])) == 1
        police.handle_receive_turn(message)
        reply = police.take_turn(now=float(turn) + 0.5)
        assert len(_fresh_centers(reply["smell_grid"])) == 1
        thief.handle_receive_turn(reply)


def test_older_trail_decays_beneath_the_fresh_center() -> None:
    police, thief = _pair()
    first = thief.take_turn(now=1.0)
    police.handle_receive_turn(first)
    thief.handle_receive_turn(police.take_turn(now=1.5))
    second = thief.take_turn(now=2.0)
    first_center = _fresh_centers(first["smell_grid"])[0]
    # Two decays later the first center reads center - 3*decay (unless re-covered by
    # the newer deposit's stronger ring — max-merge keeps whichever is higher).
    aged = round(CONSTITUTION.pheromones.center_intensity - 3 * CONSTITUTION.pheromones.decay, 3)
    assert second["smell_grid"][first_center] >= aged


def test_final_caught_message_still_deposits_scent() -> None:
    police, thief = _pair()
    police.handle_receive_turn(thief.take_turn(now=1.0))
    claim_turn = police.take_turn(now=1.5)
    claim_turn["capture_claim"] = list(thief.position)  # the claim lands
    thief.handle_receive_turn(claim_turn)
    final = thief.take_turn(now=2.0)
    assert thief.machine.state is GameState.GAME_OVER
    assert len(_fresh_centers(final["smell_grid"])) == 1  # reference send() deposits too


def test_receiver_absorbs_then_decays_its_known_field() -> None:
    police, thief = _pair()
    message = thief.take_turn(now=1.0)
    center = _fresh_centers(message["smell_grid"])[0]
    cell = tuple(int(part) for part in center.split(","))
    police.handle_receive_turn(message)
    # Absorbed at FRESH_CENTER, then one receive-side decay.
    expected = round(FRESH_CENTER - CONSTITUTION.pheromones.decay, 3)
    assert police.known_field.intensity_at((cell[0], cell[1])) == expected


def test_negotiate_payload_carries_the_locked_scent_model() -> None:
    police, _thief = _pair()
    payload = police.negotiate_payload()
    expected = locked_model_document(
        center_intensity=CONSTITUTION.pheromones.center_intensity,
        decay=CONSTITUTION.pheromones.decay,
        grid_size=CONSTITUTION.pheromones.grid_size,
        min_center_intensity=CONSTITUTION.pheromones.min_center_intensity,
    )
    assert payload["scent_model"] == expected


def test_handshake_records_both_scent_model_hashes() -> None:
    police, thief = _pair()  # _pair already ran the mutual handshake
    ours = canonical_hash(police.negotiate_payload()["scent_model"])
    assert police.scent_model_hash == ours
    assert police.opponent_scent_model_hash == ours  # same shipped config both sides
    assert thief.opponent_scent_model_hash == police.scent_model_hash


def test_handshake_tolerates_a_missing_scent_model_reference_compat() -> None:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    payload = thief.negotiate_payload()
    del payload["scent_model"]  # the reference sends only {terms, nonce, signature, identity}
    police.handle_negotiate(payload)
    assert police.opponent_scent_model_hash is None
    assert police.game_uid is not None  # the handshake itself still completes
