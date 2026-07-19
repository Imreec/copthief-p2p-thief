"""SQ2 capture-claim flow (M2, oracle sha 960499fd): claim, honest answer, final message.

The reference police claims its OWN landing cell on every moving turn — free, automatic;
the thief must answer honestly on its next turn (lying is exposed by the sealed positions
at audit); a caught thief sends the mandatory final message and both games end capture.
"""

from pathlib import Path

import pytest

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.session import PeerSession, ProtocolViolationError
from copthief_core.shared.config import load_all
from copthief_core.strategy.decision import Decision

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


class _ScriptedBrain:
    """Deterministic BrainBase stand-in: plays a scripted move list, then STAYs.

    Duck-typed against the seam's public surface — `decide` since M5-2 (`pick_move`
    kept for symmetry); the session never sees the difference (M3-5)."""

    def __init__(self, moves: list[str]) -> None:
        self._moves = list(moves)

    def pick_move(self, observation, belief) -> str:  # noqa: ANN001 - test stub
        return self._moves.pop(0) if self._moves else "STAY"

    def decide(self, observation, belief) -> "Decision":  # noqa: ANN001 - test stub
        return Decision(move=self.pick_move(observation, belief))


def _pair() -> tuple[PeerSession, PeerSession]:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    thief.handle_negotiate(police.negotiate_payload())
    police.handle_negotiate(thief.negotiate_payload())
    return police, thief


def test_police_move_turn_carries_its_landing_cell_as_capture_claim() -> None:
    police, _thief = _pair()
    police.machine.state = GameState.COMPUTING_MOVE  # as if the thief's turn arrived
    police.brain = _ScriptedBrain(["S"])
    message = police.take_turn(now=1.0)
    assert message["capture_claim"] == list(police.position)


def test_police_stay_turn_claims_nothing() -> None:
    police, _thief = _pair()
    police.machine.state = GameState.COMPUTING_MOVE
    police.brain = _ScriptedBrain(["STAY"])
    assert police.take_turn(now=1.0)["capture_claim"] is None


def test_thief_answers_a_missed_claim_honestly_and_plays_on() -> None:
    police, thief = _pair()
    police.handle_receive_turn(thief.take_turn(now=1.0))
    police.brain = _ScriptedBrain(["S"])
    claim_turn = police.take_turn(now=1.5)
    assert claim_turn["capture_claim"] is not None
    thief.handle_receive_turn(claim_turn)
    reply = thief.take_turn(now=2.0)
    assert reply["claim_response"] == {"claim": claim_turn["capture_claim"], "caught": False}
    assert thief.machine.state is GameState.AWAITING_REVEAL  # game continues


def test_caught_thief_sends_the_final_message_and_both_games_end_capture() -> None:
    police, thief = _pair()
    police.handle_receive_turn(thief.take_turn(now=1.0))
    police.brain = _ScriptedBrain(["S"])
    claim_turn = police.take_turn(now=1.5)
    claim_turn["capture_claim"] = list(thief.position)  # the claim lands on the thief
    thief.handle_receive_turn(claim_turn)
    final = thief.take_turn(now=2.0)
    assert final["claim_response"] == {"claim": list(thief.position), "caught": True}
    assert final["capture_claim"] is None
    assert final["win_claim"] is None
    assert thief.machine.state is GameState.GAME_OVER
    assert thief.outcome == "cop_capture"
    police.handle_receive_turn(final)
    assert police.machine.state is GameState.GAME_OVER
    assert police.outcome == "cop_capture"


def test_reference_final_caught_message_may_repeat_its_last_step() -> None:
    # Live finding (M5 friendly g1, 2026-07-19): the reference seals its mandatory
    # "You got me." final message at its CURRENT step (a caught thief does not move),
    # while ours increments. Both conventions are legal on the TERMINAL message only —
    # each side stays self-consistent; the audit re-hashes bytes, not grammar.
    police, thief = _pair()
    police.handle_receive_turn(thief.take_turn(now=1.0))
    police.brain = _ScriptedBrain(["S"])
    claim_turn = police.take_turn(now=1.5)
    claim_turn["capture_claim"] = list(thief.position)  # the claim lands on the thief
    thief.handle_receive_turn(claim_turn)
    final = thief.take_turn(now=2.0)
    final["step"] = 1  # rewrite to the reference convention: repeat, don't increment
    police.handle_receive_turn(final)
    assert police.machine.state is GameState.GAME_OVER
    assert police.outcome == "cop_capture"


def test_a_non_terminal_repeated_step_still_collapses_the_session() -> None:
    police, thief = _pair()
    police.handle_receive_turn(thief.take_turn(now=1.0))
    police.brain = _ScriptedBrain(["S"])
    thief.handle_receive_turn(police.take_turn(now=1.5))
    replay_turn = thief.take_turn(now=2.0)  # answers the missed claim: caught=False
    replay_turn["step"] = 1  # a repeated step WITHOUT the terminal caught answer
    with pytest.raises(ProtocolViolationError, match="step discontinuity"):
        police.handle_receive_turn(replay_turn)
