"""bestteam-thief arm pins (M13p2, ADR-0017).

Code-behavior pins from the offline study (their code EXECUTED): a diffuse
posterior makes every real move pay the CAPTURED term so STAY dominates; a sharp
posterior lets the room term climb out of corners; the trail term steers ties.
NOTE the live-tape attribution correction (golden oracle, 2026-08-17): the g02
"camp" was NOT this diffuse regime — it was 16 turns of FORCED STAY inside our
completed rule-47 cage (exit_count 0). One live mode exists: the near-
deterministic trail-driven wanderer. Fidelity: docs/evidence/m13p2-bestteam-mimic.md.
"""

from copthief_core.domain.board import Board
from copthief_core.strategy.bestteam_eval import (
    capture_risk,
    evaluate,
    k_step_reach,
    region_has_cycle,
    seal_pressure,
)
from copthief_core.strategy.bestteam_thief import THIEF_DEFAULTS, BestteamThiefBrain
from copthief_core.strategy.brains import Observation

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_board(barriers: frozenset = frozenset()) -> Board:  # type: ignore[type-arg]
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


class _Probs:
    def __init__(self, probs: dict) -> None:  # type: ignore[type-arg]
        self._probs = probs

    def probs(self) -> dict:  # type: ignore[type-arg]
        return dict(self._probs)


def _obs(board: Board, position: tuple) -> Observation:  # type: ignore[type-arg]
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role="thief",
        step=5,
        barriers_used=0,
        max_barriers=14,
    )


def _diffuse(board: Board, own: tuple) -> _Probs:  # type: ignore[type-arg]
    cells = [(r, c) for r in range(7) for c in range(7) if (r, c) != own]
    return _Probs({c: 1.0 / len(cells) for c in cells})


def test_diffuse_belief_camps() -> None:
    """Every real move pays mass * CAPTURED; STAY pays none (their executed code's
    property — reachable early-game before any frame of ours is revealed)."""
    board = make_board()
    brain = BestteamThiefBrain(seed=1)
    assert brain.pick_move(_obs(board, (3, 3)), _diffuse(board, (3, 3))) == "STAY"  # type: ignore[arg-type]


def test_sharp_belief_climbs_out_of_the_corner() -> None:
    """Sharp far cop: the room term outbids the corner — their executed finding
    (STAY 66.44 vs N/E 79.11 at (6,0), gap >> tie_epsilon)."""
    board = make_board()
    brain = BestteamThiefBrain(seed=1)
    move = brain.pick_move(_obs(board, (6, 0)), _Probs({(0, 0): 1.0}))  # type: ignore[arg-type]
    assert move in {"N", "E"}


def test_trail_avoidance_breaks_sharp_ties() -> None:
    """With the root tied, the weight_scent term steers away from own trail."""
    board = make_board()
    brain = BestteamThiefBrain(seed=1)
    obs = Observation(
        board=board,
        position=(3, 3),
        move_set=MOVE_SET,
        role="thief",
        step=5,
        barriers_used=0,
        max_barriers=14,
        own_smell={"2,3": 0.9, "3,3": 0.8, "3,2": 0.6},  # fresh trail N and W
    )
    move = brain.pick_move(obs, _Probs({(0, 0): 1.0}))  # type: ignore[arg-type]
    assert move in {"S", "E"}  # the untrailed directions


def test_eval_terms_reproduce_their_shapes() -> None:
    board = make_board()
    # room: corner 21 cells vs centre 45 within 5 steps on an open 7x7
    assert k_step_reach((6, 0), board, 5) == 21
    assert k_step_reach((3, 3), board, 5) == 45
    # open board has cycles everywhere; a sealed 1-wide dead-end corridor has none
    assert region_has_cycle((3, 3), board)
    corridor = make_board(frozenset({(1, 0), (1, 1), (0, 2), (1, 2)}))
    assert not region_has_cycle((0, 0), corridor)
    # capture_risk: adjacent cop mass counts, distant does not
    assert capture_risk((3, 3), {(3, 4): 0.7, (0, 0): 0.3}, board) == 0.7
    # seal_pressure: cheaper to seal a corner than the open centre
    assert seal_pressure((6, 0), board, 14) > seal_pressure((3, 3), board, 14)
    # evaluate is finite and centre beats corner under a far sharp cop
    weights = dict(THIEF_DEFAULTS)
    assert evaluate((3, 3), {(0, 0): 1.0}, board, 14, weights) > evaluate(
        (6, 6), {(0, 0): 1.0}, board, 14, weights
    )


def test_golden_fixture_agreement_floor() -> None:
    """The mimic's fidelity floor vs their code's own per-step scores (golden
    oracle, 2026-08-17): tie-aware agreement must never regress below 57/70.
    The number is honest, not aspirational — see ADR-0017 for the caveat."""
    import json
    from pathlib import Path

    from copthief_core.strategy.bestteam_thief import THIEF_DEFAULTS as OPTS

    rows = [
        json.loads(line)
        for line in (Path(__file__).parent / "bestteam_golden.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    brain = BestteamThiefBrain(seed=1)
    agree = 0
    for row in rows:
        board = make_board(frozenset(tuple(w) for w in row["walls"]))
        belief = {tuple(int(x) for x in k.split(",")): v for k, v in row["belief"].items()}
        pos = tuple(row["pos"])
        scores = {}
        for move, cost in row["trail_cost"].items():
            dest = board.apply_move(pos, move) if move != "STAY" else pos
            value = brain._value_of(  # noqa: SLF001 - fidelity floor reads the seam
                dest, belief, board, row["walls_left"], 2, dict(OPTS)
            )
            scores[move] = value - OPTS["weight_scent"] * cost
        best = max(scores.values())
        near = [m for m in scores if best - scores[m] <= OPTS["tie_epsilon"]]
        agree += row["chosen"] in near
    assert agree >= 57, f"golden agreement regressed: {agree}/70"
