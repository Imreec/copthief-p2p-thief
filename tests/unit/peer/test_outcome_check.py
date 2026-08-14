"""Audit-time outcome re-derivation (M11 part 2 follow-up) — the false-survival catch.

Live finding (best2934 friendly, 2026-08-14 g02/g04): our cop sealed their thief
at (6,6) with walls (5,6)+(6,5) by step 13 — rule-47 imprisonment IS capture —
and their engine never conceded, so both sub-games settled as 35-step
"survivals" with our audit data refuting the score in our own pocket. The check
is a LOUD EVENT, never a verdict change (the M6-7/SQ3 posture): a problems[]
entry accuses an honest peer of forgery, and the wall-timing boundary case
(seal completing on the final turn) makes a hard verdict unsafe.
"""

from collections.abc import Callable
from typing import Any

from copthief_core.domain.board import Board, Coord
from copthief_core.peer.outcome_check import emit_outcome_check

GRID = 7


def make_board(barriers: frozenset[Coord]) -> Board:
    return Board(
        grid_size=GRID, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers
    )


def record(step: int, cell: tuple[int, int] | None, **extra: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"step": step, "role": "THIEF", **extra}
    if cell is not None:
        payload["state"] = list(cell)  # best2934's spelling — the live-finding shape
    return {"payload": payload}


def collect(events: list[dict[str, Any]]) -> Callable[[dict[str, Any]], None]:
    return events.append


def audit(records: list[dict[str, Any]], claim: str = "survival") -> dict[str, Any]:
    return {"sender": "thief", "records": records, "result_claim": claim}


def test_the_live_g02_shape_emits_a_rule_47_mismatch() -> None:
    """Their thief camped (6,6) from step 12 to the end; our (5,6)+(6,5) walls
    imprison it. The settled 'survival' contradicts the revealed trail."""
    board = make_board(frozenset({(3, 6), (5, 6), (6, 5)}))
    records = [record(s, (6, 6) if s >= 12 else (5, 5)) for s in range(1, 36)]
    events: list[dict[str, Any]] = []
    emit_outcome_check(audit(records), board, collect(events))
    mismatches = [e for e in events if e["event"] == "outcome_mismatch"]
    assert len(mismatches) == 1
    payload = mismatches[0]["payload"]
    assert payload["rule"] == 47
    assert payload["cell"] == [6, 6]
    assert payload["held_steps"] >= 2


def test_a_wall_on_the_revealed_cell_emits_a_rule_46_mismatch() -> None:
    board = make_board(frozenset({(6, 6)}))
    records = [record(s, (6, 6)) for s in range(1, 36)]
    events: list[dict[str, Any]] = []
    emit_outcome_check(audit(records), board, collect(events))
    mismatches = [e for e in events if e["event"] == "outcome_mismatch"]
    assert len(mismatches) == 1
    assert mismatches[0]["payload"]["rule"] == 46


def test_a_true_survival_stays_silent() -> None:
    board = make_board(frozenset({(5, 6), (6, 5)}))
    records = [record(s, (3, 3)) for s in range(1, 36)]  # open cell, genuinely free
    events: list[dict[str, Any]] = []
    emit_outcome_check(audit(records), board, collect(events))
    assert [e for e in events if e["event"] == "outcome_mismatch"] == []


def test_a_final_turn_seal_is_not_flagged() -> None:
    """The boundary case that forbids a hard verdict: the thief arrives on its
    final revealed step; imprisonment never HELD across a full turn, so no
    concession window existed — the check must stay silent."""
    board = make_board(frozenset({(5, 6), (6, 5)}))
    records = [record(s, (5, 5)) for s in range(1, 35)] + [record(35, (6, 6))]
    events: list[dict[str, Any]] = []
    emit_outcome_check(audit(records), board, collect(events))
    assert [e for e in events if e["event"] == "outcome_mismatch"] == []


def test_no_revealed_coordinates_says_so_instead_of_passing_silently() -> None:
    """The M7-58 lesson: a check handed nothing must not read as a clean pass.
    anrbj666 disclose a state_digest with no coordinate — vacuity is loud."""
    board = make_board(frozenset())
    records = [record(s, None, state_digest="ab" * 16) for s in range(1, 36)]
    events: list[dict[str, Any]] = []
    emit_outcome_check(audit(records), board, collect(events))
    assert [e for e in events if e["event"] == "outcome_check_vacuous"] != []


def test_capture_claims_and_police_audits_are_out_of_scope() -> None:
    board = make_board(frozenset({(5, 6), (6, 5)}))
    records = [record(s, (6, 6)) for s in range(1, 36)]
    events: list[dict[str, Any]] = []
    emit_outcome_check(audit(records, claim="capture"), board, collect(events))
    police = {"sender": "police", "records": records, "result_claim": "survival"}
    emit_outcome_check(police, board, collect(events))
    assert [e for e in events if e["event"] == "outcome_mismatch"] == []
