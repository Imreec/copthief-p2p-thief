"""DoctrineEvaderBrain cage-escape (M11-1) — flee the ENCLOSURE, not the cop.

The M10 exposure this closes: police-m10 converts doctrine-m10 32/32 by
investing sub-threshold walls at tempo. The measured counter-shape (see
docs/evidence/m11-hardening.md): hold the central orbit zone (`center_margin`),
price a forming cage while its gap still exists (`worst_k_region`), and keep
the ruling flight floor LOW — the tempo-lift hypothesis (relocate far on
observed wall-turns) was built, measured, and removed: max-flight relocation
is rim-ward, which is exactly where a builder wants us.
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board, Coord
from copthief_core.strategy.brains import Observation
from copthief_core.strategy.doctrine_evader import DoctrineEvaderBrain

MOVE_SET = ("N", "S", "E", "W", "STAY")

ARMED = {
    "room_first": 1.0,
    "cage_escape": 1.0,
    "forecast_walls": 3.0,
    "forecast_wall_reach": 2.0,
    "flight_floor": 2.0,
    "center_margin_cap": 2.0,
}


def make_board(barriers: frozenset[Coord] = frozenset()) -> Board:
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


def make_belief(board: Board, cop_cell: Coord) -> BeliefFilter:
    return BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=cop_cell,
        center_intensity=0.9,
        decay=0.1,
        smell_trust=0.0,
        hint_trust=0.0,
    )


def make_observation(board: Board, position: Coord, *, step: int = 7) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role="thief",
        step=step,
        barriers_used=0,
        max_barriers=14,
        max_moves=35,
    )


def test_cage_escape_off_leaves_the_m10_stream_unchanged() -> None:
    """The knobs default OFF: on the same geometry the armed-and-disarmed brain and
    the plain M10 brain pick the same move (champion-gate comparability)."""
    board = make_board(frozenset({(3, 5)}))
    m10 = DoctrineEvaderBrain(seed=3, options={"room_first": 1.0})
    off = DoctrineEvaderBrain(seed=3, options={**ARMED, "cage_escape": 0.0})
    obs, belief = make_observation(board, (3, 3)), make_belief(board, (3, 1))
    assert m10.pick_move(obs, belief) == off.pick_move(obs, make_belief(board, (3, 1)))


def test_a_wall_turn_does_not_break_the_orbit_shape() -> None:
    """The removed tempo-lift hypothesis pinned in the negative: barrier growth
    between observations must NOT flip the evader into max-flight relocation
    (every measured lift variant died rim-ward). The armed brain keeps a
    floor-2-safe, margin-2 destination after a wall-turn."""
    brain = DoctrineEvaderBrain(seed=3, options=ARMED)
    before = make_board(frozenset({(3, 5)}))
    brain.pick_move(make_observation(before, (3, 3), step=1), make_belief(before, (3, 1)))
    after = make_board(frozenset({(3, 5), (2, 1)}))
    move = brain.pick_move(make_observation(after, (3, 3), step=2), make_belief(after, (3, 1)))
    dest = after.apply_move((3, 3), move)
    assert min(dest[0], 6 - dest[0], dest[1], 6 - dest[1]) >= 2  # stays in the orbit zone


def test_center_margin_outranks_the_flight_tie_break() -> None:
    """The m11 trace finding: with every room term tied on an open board, the
    DEMOTED flight tie-break still herds the evader to the rim (seed-1 death:
    a row-5 walk into the (6,0) corner). The margin term holds the orbit zone:
    at (4,4) with the cop far away, rim-ward S/E (margin 1) lose to N/W
    (margin 2) even though they are farther from the cop."""
    board = make_board()
    armed = DoctrineEvaderBrain(seed=3, options=ARMED)
    move = armed.pick_move(make_observation(board, (4, 4)), make_belief(board, (0, 0)))
    assert move in {"N", "W"}


def test_the_nisyar1_g02_corner_step_is_refused() -> None:
    """The 2026-08-11 live kill, pinned at its decisive step: us at (6,5), their
    cop exactly known at (5,4) (they claim every turn). The live M10 doctrine
    took E into (6,6), was pinned at the diagonal and sealed with two walls.
    The k-wall forecast prices (6,6) as a two-wall pocket (region 1) and holds
    (6,5) instead — both remaining moves are lethal-gated."""
    board = make_board()
    armed = DoctrineEvaderBrain(seed=3, options=ARMED)
    move = armed.pick_move(make_observation(board, (6, 5)), make_belief(board, (5, 4)))
    assert move != "E"


def test_the_k_wall_forecast_holds_the_closing_gap() -> None:
    """A four-wall cut down column 3 with the gap at rows 4-6 and the builder at
    (6,3): the west side is three walls from sealed. The one-wall room terms
    prefer W (more escapes today); the k-wall forecast prices the pocket and takes
    E onto the gap column — through it while it exists."""
    board = make_board(frozenset({(0, 3), (1, 3), (2, 3), (3, 3)}))
    obs, belief = make_observation(board, (4, 2)), make_belief(board, (6, 3))
    m10 = DoctrineEvaderBrain(seed=3, options={"room_first": 1.0})
    armed = DoctrineEvaderBrain(seed=3, options=ARMED)
    assert m10.pick_move(obs, belief) == "W"
    assert armed.pick_move(obs, make_belief(board, (6, 3))) == "E"
