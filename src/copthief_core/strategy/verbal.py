"""Referee-mode verbal layer (TODO M5-6): hints against ground truth.

Threads a thief Decision's hint fields through the SAME semantics as the peer
inbound path — compose → closed-vocabulary parse → `update_hint`, after the
belief's predict+scent — and records what the hint DID to the tracker, measurable
only here, where the harness knows the true thief cell: error = 1 − P(truth), the
M3-3 metric identity. The verbal layer never touches moves (App E rule 25).
"""

from __future__ import annotations

from dataclasses import dataclass

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Coord
from copthief_core.domain.gazetteer import Gazetteer
from copthief_core.strategy.decision import Decision
from copthief_core.strategy.hints import VERDICT_TRUTH, compose_hint


@dataclass(frozen=True)
class HintTraceRow:
    """One hint's measured effect on the police belief (referee truth-anchored)."""

    step: int
    verdict: str
    error_before: float
    error_after: float


def belief_error(belief: BeliefFilter, truth: Coord) -> float:
    """1 − P(true cell) — the M3-3 belief-error identity (0 = certain and right)."""
    return 1.0 - belief.probs().get(truth, 0.0)


def apply_thief_hint(
    gazetteer: Gazetteer,
    *,
    decision: Decision,
    truth: Coord,
    belief: BeliefFilter,
    max_words: int,
    salt: int,
    bank: str,
    trace: list[HintTraceRow] | None,
) -> None:
    """Compose the turn's hint, feed it to the police belief, record the delta.

    Mirrors peer/turns + peer/inbound: a silent decision composes as the truthful
    default; the wire text reaches the belief only through the closed-vocabulary
    parser (adversarial-input stance holds even against ourselves).
    """
    composed = compose_hint(
        gazetteer,
        position=truth,
        max_words=max_words,
        salt=salt,
        verdict=decision.hint_verdict or VERDICT_TRUTH,
        landmark=decision.hint_landmark,
        bank=bank,
    )
    error_before = belief_error(belief, truth)
    landmark = gazetteer.parse(composed.text, max_words=max_words)
    if landmark is not None:
        belief.update_hint(gazetteer.cells_for(landmark))
    if trace is not None:
        trace.append(
            HintTraceRow(
                step=salt,
                verdict=composed.verdict,
                error_before=error_before,
                error_after=belief_error(belief, truth),
            )
        )
