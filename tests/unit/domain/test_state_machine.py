"""Game state machine (PLAN §5): exhaustive transition-space property tests.

The state space is finite (7 states → 49 ordered pairs), so the "property" is proven by
exhaustion, not sampling: every pair outside the PLAN §5 table must raise, every pair
inside it must succeed — no illegal transition can hide.
"""

import pytest

from copthief_core.domain.state_machine import (
    GameState,
    GameStateMachine,
    IllegalTransitionError,
)

S = GameState

# The PLAN §5 table, verbatim: comm-state cycle, two terminal exits, and the
# any-comm-state → TECHNICAL_LOSS escape hatch.
LEGAL: set[tuple[GameState, GameState]] = {
    (S.WAITING_FOR_OPPONENT, S.COMPUTING_MOVE),
    (S.COMPUTING_MOVE, S.COMMITTING),
    (S.COMMITTING, S.AWAITING_REVEAL),
    (S.AWAITING_REVEAL, S.VERIFYING),
    (S.VERIFYING, S.WAITING_FOR_OPPONENT),
    (S.VERIFYING, S.GAME_OVER),
    (S.WAITING_FOR_OPPONENT, S.TECHNICAL_LOSS),
    (S.COMPUTING_MOVE, S.TECHNICAL_LOSS),
    (S.COMMITTING, S.TECHNICAL_LOSS),
    (S.AWAITING_REVEAL, S.TECHNICAL_LOSS),
    (S.VERIFYING, S.TECHNICAL_LOSS),
}


@pytest.mark.parametrize("source", list(GameState))
@pytest.mark.parametrize("target", list(GameState))
def test_every_transition_pair_matches_the_plan_table(source: GameState, target: GameState) -> None:
    machine = GameStateMachine(state=source)
    if (source, target) in LEGAL:
        assert machine.advance(target) is target
        assert machine.state is target
    else:
        with pytest.raises(IllegalTransitionError, match=f"{source.name}.*{target.name}"):
            machine.advance(target)
        assert machine.state is source  # a refused transition never mutates state


@pytest.mark.parametrize("terminal", [S.GAME_OVER, S.TECHNICAL_LOSS])
def test_terminal_states_absorb(terminal: GameState) -> None:
    machine = GameStateMachine(state=terminal)
    assert machine.is_terminal
    for target in GameState:
        with pytest.raises(IllegalTransitionError):
            machine.advance(target)


def test_full_happy_minigame_walk_ends_in_game_over() -> None:
    machine = GameStateMachine(state=S.WAITING_FOR_OPPONENT)
    for _ in range(3):  # a few turn cycles
        machine.advance(S.COMPUTING_MOVE)
        machine.advance(S.COMMITTING)
        machine.advance(S.AWAITING_REVEAL)
        machine.advance(S.VERIFYING)
        machine.advance(S.WAITING_FOR_OPPONENT)
    machine.advance(S.COMPUTING_MOVE)
    machine.advance(S.COMMITTING)
    machine.advance(S.AWAITING_REVEAL)
    machine.advance(S.VERIFYING)
    machine.advance(S.GAME_OVER)
    assert machine.is_terminal


def test_first_mover_starts_at_computing_move() -> None:
    machine = GameStateMachine(state=S.COMPUTING_MOVE)
    assert not machine.is_terminal
    machine.advance(S.COMMITTING)
    assert machine.state is S.COMMITTING
