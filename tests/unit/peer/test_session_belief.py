"""F9 closure + belief wiring in the session (PRD_belief §2.2, §4; spike §8 gap 1).

F9 (M2 residual): our session validated inbound `barrier_placed` but never noted it —
our own move legality ignored opponent barriers (the g2 scenario: the reference cop
placed 7 barriers; our thief crossed one cell legally only by luck). These tests fail
against the M2-era behavior by construction.
"""

from pathlib import Path

from copthief_core.domain.rules import legal_moves
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


def _pair() -> tuple[PeerSession, PeerSession]:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    thief.handle_negotiate(police.negotiate_payload())
    police.handle_negotiate(thief.negotiate_payload())
    return police, thief


def _police_turn_with_barrier(police: PeerSession, cell: tuple[int, int]) -> dict:
    message = police.take_turn(now=1.5)
    message["barrier_placed"] = list(cell)  # as if their brain placed it this turn
    return message


def test_f9_regression_inbound_barrier_enters_our_own_move_legality() -> None:
    police, thief = _pair()
    police.handle_receive_turn(thief.take_turn(now=1.0))
    barrier = (thief.position[0], thief.position[1] - 1)  # west of our thief
    thief.handle_receive_turn(_police_turn_with_barrier(police, barrier))
    # The M2-era session left the board barrier-free here — this is the failing pin.
    assert barrier in thief.board.barriers
    assert "W" not in legal_moves(thief.board, thief.position, CONSTITUTION.movement.move_set)


def test_f9_regression_g2_scenario_our_mover_never_enters_a_declared_barrier() -> None:
    police, thief = _pair()
    police.handle_receive_turn(thief.take_turn(now=1.0))
    barrier = (thief.position[0], thief.position[1] - 1)
    thief.handle_receive_turn(_police_turn_with_barrier(police, barrier))
    for turn in range(6):  # a seeded walk can no longer cross the declared cell
        message = thief.take_turn(now=2.0 + turn)
        assert tuple(thief.position) != barrier
        police.handle_receive_turn(message)
        thief.handle_receive_turn(police.take_turn(now=2.5 + turn))
        assert tuple(thief.position) != barrier


def test_inbound_barrier_constrains_the_belief_motion_model() -> None:
    police, thief = _pair()
    police.handle_receive_turn(thief.take_turn(now=1.0))
    barrier = (2, 3)
    thief.handle_receive_turn(_police_turn_with_barrier(police, barrier))
    thief.belief.predict()
    assert thief.belief.prob_at(barrier) == 0.0


def test_belief_tracks_the_opponent_from_the_signed_start() -> None:
    police, thief = _pair()
    # Before any inbound turn: the prior is a delta at the opponent's signed start.
    assert police.belief.prob_at(CONSTITUTION.board.thief_start) == 1.0
    assert thief.belief.prob_at(CONSTITUTION.board.cop_start) == 1.0


def test_inbound_turn_runs_predict_then_scent_update() -> None:
    police, thief = _pair()
    message = thief.take_turn(now=1.0)
    police.handle_receive_turn(message)
    # After one thief turn: support spread beyond the start, sharpened by the fresh
    # center their honest grid transmitted at the new position.
    fresh = round(CONSTITUTION.pheromones.center_intensity - CONSTITUTION.pheromones.decay, 3)
    center = next(
        tuple(int(p) for p in key.split(","))
        for key, value in message["smell_grid"].items()
        if value == fresh
    )
    assert police.belief.argmax() == center  # the honest fresh center wins the argmax
    assert 0.0 < police.belief.prob_at(center) < 1.0  # sharpened, never certain
    assert len(police.belief.probs()) > 1  # predict spread the support first


def test_private_settings_carry_the_belief_trust_tuning() -> None:
    assert PRIVATE.smell_trust_weight > 0.0
    assert PRIVATE.hint_trust_default > 0.0
