"""Hint composition (TODO M3-4): template bank × gazetteer, word-capped, round-trip.

DoD pin: every hint WE compose parses back through OUR OWN parser to the landmark it
was built from (PLAN §13 M3). Verdicts use the reference vocabulary ("truth"/"lie",
its constants VERDICT_TRUTH/VERDICT_LIE); deception TIMING stays M5 — here `truth` is
the default and `lie` is only the mechanism.
"""

import pytest

from copthief_core.domain.board import Board
from copthief_core.domain.gazetteer import Gazetteer
from copthief_core.strategy.hints import VERDICT_LIE, VERDICT_TRUTH, compose_hint

PAYLOAD = {
    "areas": {
        "Testville": {
            "landmarks": {
                "Old Mill": {"row_frac": 0.0, "col_frac": 0.0, "radius": 1},
                "Market Square": {"row_frac": 0.5, "col_frac": 0.5, "radius": 1},
                "South Docks": {"row_frac": 1.0, "col_frac": 0.5, "radius": 1},
            }
        }
    }
}
MAX_WORDS = 15


def make_gazetteer() -> Gazetteer:
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    return Gazetteer.from_payload(PAYLOAD, map_area="Testville", board=board)


def test_truthful_hint_names_the_nearest_landmark_and_round_trips() -> None:
    gazetteer = make_gazetteer()
    composed = compose_hint(gazetteer, position=(0, 1), max_words=MAX_WORDS, salt=0)
    assert composed.verdict == VERDICT_TRUTH
    assert composed.landmark == "Old Mill"
    assert gazetteer.parse(composed.text, max_words=MAX_WORDS) == "Old Mill"


def test_every_template_round_trips_for_every_landmark() -> None:
    gazetteer = make_gazetteer()
    for salt in range(12):  # walks the whole bank at least twice
        for position in [(0, 0), (3, 3), (6, 3)]:
            composed = compose_hint(gazetteer, position=position, max_words=MAX_WORDS, salt=salt)
            assert gazetteer.parse(composed.text, max_words=MAX_WORDS) == composed.landmark
            assert len(composed.text.split()) <= MAX_WORDS


def test_salt_varies_the_template_deterministically() -> None:
    gazetteer = make_gazetteer()
    first = compose_hint(gazetteer, position=(3, 3), max_words=MAX_WORDS, salt=0)
    again = compose_hint(gazetteer, position=(3, 3), max_words=MAX_WORDS, salt=0)
    second = compose_hint(gazetteer, position=(3, 3), max_words=MAX_WORDS, salt=1)
    assert first == again
    assert first.text != second.text
    assert first.landmark == second.landmark  # the salt changes wording, not truth


def test_lie_hint_names_a_landmark_far_from_us() -> None:
    gazetteer = make_gazetteer()
    composed = compose_hint(
        gazetteer, position=(0, 0), max_words=MAX_WORDS, salt=0, verdict=VERDICT_LIE
    )
    assert composed.verdict == VERDICT_LIE
    assert composed.landmark == "South Docks"
    assert (0, 0) not in gazetteer.cells_for(composed.landmark)
    assert gazetteer.parse(composed.text, max_words=MAX_WORDS) == "South Docks"


def test_tight_word_cap_still_round_trips() -> None:
    gazetteer = make_gazetteer()
    composed = compose_hint(gazetteer, position=(3, 3), max_words=5, salt=0)
    assert len(composed.text.split()) <= 5
    assert gazetteer.parse(composed.text, max_words=5) == composed.landmark


def test_empty_gazetteer_refuses_composition() -> None:
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    empty = Gazetteer.from_payload(PAYLOAD, map_area="Atlantis", board=board)
    with pytest.raises(ValueError, match="no landmarks"):
        compose_hint(empty, position=(3, 3), max_words=MAX_WORDS, salt=0)
