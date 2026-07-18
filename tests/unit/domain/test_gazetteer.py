"""Gazetteer (TODO M3-4; PLAN §8): map_area landmarks ↔ board cells, closed-world parse.

The gazetteer is OUR private reading of the signed `world.map_area` — fractional
anchors resolve onto whatever grid size was signed, and the parser is a CLOSED
vocabulary matcher: opponent text can only ever map to a known landmark or to None
(App E: opponent text is adversarial input; it never reaches anything with authority).
"""

from copthief_core.domain.board import Board
from copthief_core.domain.gazetteer import Gazetteer

PAYLOAD = {
    "version": "1.00",
    "areas": {
        "Testville": {
            "landmarks": {
                "Old Mill": {"row_frac": 0.0, "col_frac": 0.0, "radius": 1},
                "Market Square": {"row_frac": 0.5, "col_frac": 0.5, "radius": 1},
                "South Docks": {"row_frac": 1.0, "col_frac": 0.5, "radius": 1},
            }
        }
    },
}


def make_gazetteer(grid_size: int = 7, origin: int = 0) -> Gazetteer:
    board = Board(grid_size=grid_size, axis_origin_corner="top-left", axis_start_index=origin)
    return Gazetteer.from_payload(PAYLOAD, map_area="Testville", board=board)


def test_fractional_anchors_resolve_onto_the_signed_grid() -> None:
    gazetteer = make_gazetteer(grid_size=7)
    assert (3, 3) in gazetteer.cells_for("Market Square")  # 0.5 of a 7-grid -> row 3
    assert (0, 0) in gazetteer.cells_for("Old Mill")
    assert (6, 3) in gazetteer.cells_for("South Docks")


def test_landmark_cells_are_chebyshev_balls_clipped_to_the_board() -> None:
    gazetteer = make_gazetteer(grid_size=7)
    market = gazetteer.cells_for("Market Square")
    assert set(market) == {(r, c) for r in (2, 3, 4) for c in (2, 3, 4)}
    mill = gazetteer.cells_for("Old Mill")  # corner anchor: 3x3 clipped to 2x2
    assert set(mill) == {(0, 0), (0, 1), (1, 0), (1, 1)}


def test_anchors_scale_with_a_different_signed_grid_size() -> None:
    gazetteer = make_gazetteer(grid_size=10)
    assert (9, 4) in gazetteer.cells_for("South Docks")  # 1.0 -> last row + 0.5 -> col 4
    board_cells = {cell for name in gazetteer.landmarks() for cell in gazetteer.cells_for(name)}
    assert all(0 <= r < 10 and 0 <= c < 10 for r, c in board_cells)


def test_parse_finds_landmarks_case_insensitively_inside_sentences() -> None:
    gazetteer = make_gazetteer()
    assert gazetteer.parse("I heard sirens near MARKET square.", max_words=15) == "Market Square"
    assert gazetteer.parse("the old mill, again", max_words=15) == "Old Mill"


def test_parse_returns_none_for_unknown_or_empty_text() -> None:
    gazetteer = make_gazetteer()
    assert gazetteer.parse("nothing to see here", max_words=15) is None
    assert gazetteer.parse("", max_words=15) is None


def test_parse_reads_at_most_the_signed_word_cap() -> None:
    gazetteer = make_gazetteer()
    padded = ("waffle " * 15) + "Market Square"  # the landmark sits past the cap
    assert gazetteer.parse(padded, max_words=15) is None
    assert gazetteer.parse(padded, max_words=17) == "Market Square"


def test_parse_prefers_the_longest_match_deterministically() -> None:
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    payload = {
        "areas": {
            "Nested": {
                "landmarks": {
                    "Park": {"row_frac": 0.0, "col_frac": 1.0, "radius": 0},
                    "Park Avenue": {"row_frac": 1.0, "col_frac": 1.0, "radius": 0},
                }
            }
        }
    }
    gazetteer = Gazetteer.from_payload(payload, map_area="Nested", board=board)
    assert gazetteer.parse("meet me on park avenue", max_words=15) == "Park Avenue"
    assert gazetteer.parse("just the park", max_words=15) == "Park"


def test_nearest_and_farthest_are_deterministic() -> None:
    gazetteer = make_gazetteer()
    assert gazetteer.nearest((0, 1)) == "Old Mill"
    assert gazetteer.farthest((0, 0)) == "South Docks"
    # Ties break lexicographically, reproducibly.
    assert gazetteer.nearest((3, 3)) == "Market Square"


def test_unknown_map_area_yields_an_empty_closed_world() -> None:
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    gazetteer = Gazetteer.from_payload(PAYLOAD, map_area="Atlantis", board=board)
    assert gazetteer.landmarks() == ()
    assert gazetteer.parse("Market Square", max_words=15) is None
