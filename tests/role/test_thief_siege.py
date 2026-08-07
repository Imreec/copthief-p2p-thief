"""Siege-conditional support width (M7-46) — ⚑ thief repo only.

The flight vector averages the distance to the `top_k` most likely cop cells. That
hedge is right against a pursuer we can only localise loosely, and wrong against one
that walls every turn: a sieging cop closes the gap far faster than a smeared support
lets us flee, and the 2026-08-07 uoh-sqak friendly lost all three thief sub-games to
exactly that. The wall RATE is observable from our own board, so the brain narrows the
support only once the opponent has proved itself a sieger — a cop that rarely walls
never trips the condition, which is what keeps the arena's existing arms untouched.
"""

from copthief_core.domain.board import Board
from copthief_core.strategy.brains import Observation
from copthief_thief.features import resolve_options, support_width, under_siege

MOVE_SET = ("N", "S", "E", "W", "STAY")
OPTS = resolve_options({})


def make_board(barriers: frozenset = frozenset()) -> Board:  # type: ignore[type-arg]
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


def observation(board: Board, position: tuple[int, int], *, step: int) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role="thief",
        step=step,
        barriers_used=0,  # a thief never places one — the signal must be the board
        max_barriers=14,
        survival_threshold=35,
        max_moves=35,
    )


def sieged(walls: int, step: int) -> Observation:
    """An observation whose board carries `walls` barriers at `step`."""
    cells = frozenset({(0, index) for index in range(walls)})
    assert len(cells) == walls, "fixture must place distinct barriers"
    return observation(make_board(cells), (3, 3), step=step)


def test_open_board_is_never_a_siege() -> None:
    assert under_siege(OPTS, sieged(0, 1)) is False


def test_below_the_minimum_wall_count_is_never_a_siege() -> None:
    """One early wall is noise, not a siege — the absolute floor must gate the rate."""
    assert under_siege(OPTS, sieged(1, 2)) is False


def test_a_cop_walling_every_turn_is_a_siege() -> None:
    assert under_siege(OPTS, sieged(6, 7)) is True


def test_an_occasional_waller_is_not_a_siege() -> None:
    """`ref-police` walls at 0.15 — the rate gate must leave that regime alone."""
    assert under_siege(OPTS, sieged(3, 21)) is False


def test_support_width_is_the_configured_top_k_off_siege() -> None:
    assert support_width(OPTS, sieged(0, 1)) == int(OPTS["top_k"])


def test_support_width_narrows_under_siege() -> None:
    assert support_width(OPTS, sieged(6, 7)) == int(OPTS["siege_top_k"])


def test_support_width_honours_config_overrides() -> None:
    opts = resolve_options({"siege_top_k": 2.0, "siege_min_walls": 2.0})
    assert support_width(opts, sieged(6, 7)) == 2


def test_siege_reads_the_board_not_the_thief_quota() -> None:
    """A thief's own `barriers_used` is always 0 — the signal must be the board."""
    board = Board(
        grid_size=7,
        axis_origin_corner="top-left",
        axis_start_index=0,
        barriers=frozenset({(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6)}),
    )
    assert under_siege(OPTS, observation(board, (3, 3), step=7)) is True


def test_a_distant_threat_keeps_the_tuned_hedge() -> None:
    """Far away, which exact cell the cop occupies barely moves the flight vector."""
    assert support_width(OPTS, sieged(0, 5), 6) == int(OPTS["top_k"])


def test_a_close_threat_narrows_to_the_argmax() -> None:
    """M7-51. In the 2026-08-08 friendly our thief stepped WEST from (0,6) onto the cop
    at (0,5) with the argmax already CORRECT — averaging four candidate cells, not the
    belief, chose that move. Inside `close_threat_distance` we flee the argmax itself."""
    assert support_width(OPTS, sieged(0, 5), 2) == int(OPTS["siege_top_k"])


def test_the_close_threat_gate_is_configurable_and_can_be_shut() -> None:
    opts = resolve_options({"close_threat_distance": -1.0})
    assert support_width(opts, sieged(0, 5), 0) == int(opts["top_k"])


def test_omitting_the_gap_reproduces_the_pre_m7_51_width() -> None:
    """Callers that do not pass a gap must be byte-identical to before."""
    assert support_width(OPTS, sieged(0, 5)) == int(OPTS["top_k"])
    assert support_width(OPTS, sieged(6, 7)) == int(OPTS["siege_top_k"])
