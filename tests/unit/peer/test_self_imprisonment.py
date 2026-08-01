"""M7-29: the thief adjudicates rules 46/47 against ITSELF (App E p.149, source ch.3).

The warm-up defect the opponent team found (Round 20, verified from our own sealed
records): our cop and our referee both consume `is_imprisoned`, but the peer-path
thief never ran it on its own cell — in s1/s3/s5 it sat sealed at (6,6) for 23 turns
and claimed survival. Rule 46: a barrier placed on the thief's cell is a capture.
Rule 47: a thief imprisoned with no legal move is captured. The fix: after folding an
inbound barrier, the thief runs the same predicate its opponent's cop runs and
concedes through the existing caught-final shape — sealed, automatic, no strategy
input in the path (the opponent team's `i_am_captured` design, credited).
"""

from pathlib import Path

from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)

CORNER = (6, 6)  # the SE corner of the 7x7 board: neighbors (5,6) and (6,5) only
GATES = ((5, 6), (6, 5))


def _pair() -> tuple[PeerSession, PeerSession]:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    thief.handle_negotiate(police.negotiate_payload())
    police.handle_negotiate(thief.negotiate_payload())
    return police, thief


def _police_turn_with_barrier(police: PeerSession, cell: tuple[int, int]) -> dict:
    message = police.take_turn(now=1.5)
    message["barrier_placed"] = list(cell)  # as if their brain placed it this turn
    message["capture_claim"] = None  # SQ2: a barrier turn never claims
    return message


def _seal_the_corner(police: PeerSession, thief: PeerSession) -> None:
    """Drive the warm-up scenario: thief at the corner, both gates walled inbound."""
    police.handle_receive_turn(thief.take_turn(now=1.0))
    thief.handle_receive_turn(_police_turn_with_barrier(police, GATES[0]))
    police.handle_receive_turn(thief.take_turn(now=2.0))
    thief.position = CORNER  # the scenario's position at the moment the seal lands
    thief.handle_receive_turn(_police_turn_with_barrier(police, GATES[1]))


def test_rule_47_a_sealed_thief_concedes_at_the_moment_of_imprisonment() -> None:
    police, thief = _pair()
    _seal_the_corner(police, thief)
    assert thief.caught  # captured at the seal, not at some later adjudication
    assert thief.pending_claim_response == {"claim": list(CORNER), "caught": True}


def test_rule_47_the_concede_final_is_the_mandatory_caught_shape() -> None:
    police, thief = _pair()
    _seal_the_corner(police, thief)
    final = thief.take_turn(now=3.0)
    assert final["claim_response"] == {"claim": list(CORNER), "caught": True}
    assert final["win_claim"] is None  # the s1/s3/s5 bug shape: never survival
    assert thief.records[-1].payload["move"] == "STAY"
    assert thief.outcome == "cop_capture"


def test_rule_47_the_sealing_cop_settles_capture_from_the_concede_final() -> None:
    police, thief = _pair()
    _seal_the_corner(police, thief)
    police.handle_receive_turn(thief.take_turn(now=3.0))
    assert police.outcome == "cop_capture"


def test_rule_46_a_barrier_on_the_thiefs_own_cell_is_a_capture() -> None:
    police, thief = _pair()
    police.handle_receive_turn(thief.take_turn(now=1.0))
    thief.handle_receive_turn(_police_turn_with_barrier(police, tuple(thief.position)))
    assert thief.caught
    assert thief.pending_claim_response == {"claim": list(thief.position), "caught": True}


def test_one_open_gate_is_not_imprisonment() -> None:
    police, thief = _pair()
    police.handle_receive_turn(thief.take_turn(now=1.0))
    thief.position = CORNER
    thief.handle_receive_turn(_police_turn_with_barrier(police, GATES[0]))
    assert not thief.caught  # (6,5) is still an escape
    assert thief.pending_claim_response is None


def test_a_police_session_never_self_concedes_on_an_inbound_barrier() -> None:
    # Rules 46/47 capture the THIEF. A barrier arriving at a police session (illegal
    # in the game, tolerated on the wire) must not trip the thief's concession path —
    # even when it completes a seal around the police's own cell.
    police, thief = _pair()
    police.position = CORNER
    police.board = police.board.with_barrier(GATES[0])
    message = thief.take_turn(now=1.0)
    message["barrier_placed"] = list(GATES[1])
    message["capture_claim"] = None
    police.handle_receive_turn(message)
    assert not police.caught
    assert police.pending_claim_response is None
