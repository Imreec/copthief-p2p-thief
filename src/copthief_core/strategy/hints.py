"""Hint composition (TODO M3-4): template bank × gazetteer, word-capped, round-trip.

The verbal layer NEVER decides moves (App E rule 25) — it only narrates. Templates are
fixed strings with one {landmark} slot, so composition is generation-by-lookup: zero
tokens, zero opponent influence. Verdict vocabulary mirrors the reference constants
(VERDICT_TRUTH/VERDICT_LIE): `truth` names our nearest landmark, `lie` the farthest —
the lie MECHANISM ships here, its TIMING is a brain decision (M5).
"""

from __future__ import annotations

from dataclasses import dataclass

from copthief_core.domain.board import Coord
from copthief_core.domain.gazetteer import Gazetteer

VERDICT_TRUTH = "truth"
VERDICT_LIE = "lie"

# Every template must round-trip: parse(render(landmark)) == landmark for the whole
# bank × every shipped landmark (unit-enforced). Keep the slot early — the word cap
# truncates from the right. M5-6: named banks; the A/B arena run measures deception
# efficacy across them and the winner ships in `[strategy] hint_bank`. Wording is
# neutral to OUR closed-vocabulary parser by construction — measurable differences
# come from parse survival under the signed word cap and from the decoy policy
# (disclosed in the A/B evidence).
DEFAULT_BANK = "classic"
BANKS: dict[str, tuple[str, ...]] = {
    "classic": (
        "They say the crowds near {landmark} hide anyone.",
        "I heard sirens somewhere around {landmark}.",
        "The shadows by {landmark} feel busy tonight.",
        "Word is, keep an eye on {landmark}.",
        "Someone was asking about {landmark} just now.",
        "All roads seem to lead to {landmark}.",
    ),
    "terse": (
        "Near {landmark}, maybe.",
        "Watch {landmark} tonight.",
        "Try {landmark}.",
        "Around {landmark} somewhere.",
    ),
}
# The guaranteed-short fallback when the signed word cap is tighter than the bank.
_SHORT_TEMPLATE = "Near {landmark}."


@dataclass(frozen=True)
class ComposedHint:
    """One rendered hint: the wire text, the sealed verdict, and its landmark."""

    text: str
    verdict: str
    landmark: str


def compose_hint(
    gazetteer: Gazetteer,
    *,
    position: Coord,
    max_words: int,
    salt: int,
    verdict: str = VERDICT_TRUTH,
    landmark: str | None = None,
    bank: str = "",
) -> ComposedHint:
    """Render one hint (Input: gazetteer + our true position + the signed word cap +
    a determinism salt + the intended verdict + an optional explicit landmark;
    Output: ComposedHint; Raises: ValueError on an empty gazetteer — composing
    without geography would fabricate).

    `truth` names the landmark nearest our position, `lie` the farthest — unless the
    caller picks the landmark itself (the M5-3 decoy seam; off-vocabulary picks fall
    back to the default so the closed world never leaks). The salt cycles the
    template bank so runs stay deterministic per (salt, position); an unknown or
    empty `bank` resolves to the default bank (M5-6: never fabricate).
    """
    if not gazetteer.landmarks():
        raise ValueError("no landmarks for the signed map_area - cannot compose hints")
    if landmark is None or landmark not in gazetteer.landmarks():
        landmark = (
            gazetteer.nearest(position)
            if verdict == VERDICT_TRUTH
            else (gazetteer.farthest(position))
        )
    templates = BANKS.get(bank) or BANKS[DEFAULT_BANK]
    text = templates[salt % len(templates)].format(landmark=landmark)
    if len(text.split()) > max_words:
        text = _SHORT_TEMPLATE.format(landmark=landmark)
    return ComposedHint(text=text, verdict=verdict, landmark=landmark)
