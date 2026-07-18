"""ThiefBrain invariants (PRD_thief_brain §7/§8) — ⚑ thief repo only.

The App-E-rule-25 pin: no LLM machinery anywhere near the decision path — enforced
structurally (AST import scan over the role package + core strategy), the sibling
repo's technique. Plus the generous per-decision perf ceiling and a legality property.
"""

import ast
import time
from pathlib import Path

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board
from copthief_core.domain.rules import is_legal_move
from copthief_core.strategy.brains import Observation
from copthief_thief.brain import ThiefBrain
from copthief_thief.features import resolve_options

MOVE_SET = ("N", "S", "E", "W", "STAY")


def test_no_llm_machinery_anywhere_near_the_decision_path() -> None:
    sources = [
        *Path("src/copthief_thief").rglob("*.py"),
        *Path("src/copthief_core/strategy").rglob("*.py"),
    ]
    assert sources
    for path in sources:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom | ast.Import):
                imported = getattr(node, "module", "") or ""
                targets = [imported, *[a.name for a in node.names]]
                assert not any("llm" in t or "infra" in t for t in targets), (
                    f"{path}: the move decision must stay pure Python (App E rule 25)"
                )


def test_decisions_stay_legal_over_scattered_boards() -> None:
    board = Board(
        grid_size=7,
        axis_origin_corner="top-left",
        axis_start_index=0,
        barriers=frozenset({(1, 1), (2, 4), (4, 2), (5, 5), (3, 0)}),
    )
    brain = ThiefBrain(seed=3)
    for thief in [(0, 0), (3, 3), (6, 6), (0, 6), (6, 0)]:
        for believed in [(0, 5), (5, 0), (3, 4), (6, 3)]:
            belief = BeliefFilter(
                board=board,
                move_set=MOVE_SET,
                start=believed,
                center_intensity=0.9,
                decay=0.1,
                smell_trust=4.0,
                hint_trust=1.0,
            )
            observation = Observation(
                board=board,
                position=thief,
                move_set=MOVE_SET,
                role="thief",
                step=1,
                barriers_used=5,
                max_barriers=14,
            )
            decision = brain.decide(observation, belief)
            assert decision.barrier is None  # the barrier law is police-only
            assert is_legal_move(board, thief, decision.move, MOVE_SET)


def test_one_decision_fits_the_configured_budget() -> None:
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    belief = BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=(0, 0),
        center_intensity=0.9,
        decay=0.1,
        smell_trust=4.0,
        hint_trust=1.0,
    )
    for _ in range(6):  # spread the mass so the support is genuinely multi-modal
        belief.predict()
    observation = Observation(
        board=board,
        position=(6, 6),
        move_set=MOVE_SET,
        role="thief",
        step=7,
        barriers_used=0,
        max_barriers=14,
    )
    brain = ThiefBrain(seed=1)
    started = time.perf_counter()
    brain.decide(observation, belief)
    elapsed = time.perf_counter() - started
    assert elapsed <= resolve_options({})["decision_budget_seconds"]
