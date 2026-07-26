"""BeliefEvaderBrain — the trap-aware evader opponent model (M7-14).

The arena stand-in for the opponent team's announced rematch counter, with the
priority order the M7-13 capture postmortem dictates: (1) flee the BELIEVED cop —
both friendly captures were failures of opponent-position modeling, not trap-dodging;
(2) refuse to camp under threat — a stationary thief is a self-refreshing beacon
under `multiplicative_book_v1`, and in corner geometry STAY even MAXIMIZES Manhattan
distance, which is exactly the g02 losing pattern; (3) forecast walls — destination
mobility plus reachable region, the opponent's announced "belief-native wall
forecast". Belief-native throughout: it reads the filter's full distribution, so the
same brain models his current scent-belief evader (hidden feed), his announced fix
(same feed, these terms), and a claim-reading evader (LagTruthFeed).

`DEFAULT_OPTIONS` is a data table, not logic (the features.py pattern): arena
`brain_options` overrides any knob, which is how the measurement's ablation arms
(no-penalty, no-forecast) are expressed in config rather than code.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.region import region_size

DEFAULT_OPTIONS: dict[str, float] = {
    "w_cop_distance": 1.0,  # expected (Manhattan + Chebyshev) distance from the believed cop
    "w_mobility": 0.3,  # legal moves available from the destination
    "w_region": 0.1,  # reachable open region from the destination (wall forecast)
    "region_cap": 24.0,  # BFS early-exit: beyond this a region counts as "open"
    "stay_penalty": 2.0,  # camping cost while the believed cop is inside the radius
    "stay_penalty_radius": 2.0,  # threat radius in Chebyshev (capture geometry)
}


class BeliefEvaderBrain(BrainBase):
    """Belief-native evasion: maximize expected flight distance, avoid pockets,
    never camp under threat. Deterministic: ties break on sorted move order."""

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        opts = {**DEFAULT_OPTIONS, **self._options}
        board = observation.board
        probs = belief.probs()
        cache: dict[Coord, int] = {}
        candidates = sorted(legal_moves(board, observation.position, observation.move_set))
        if not candidates:
            return STAY

        def expected_flight(cell: Coord) -> float:
            """Expected Manhattan + Chebyshev distance: Manhattan alone leaves every
            perpendicular move tied with straight flight (and in corner geometry
            crowns STAY — the g02 camp); the Chebyshev term breaks both toward
            genuinely increasing separation."""
            return sum(
                p * (abs(cell[0] - cop[0]) + abs(cell[1] - cop[1]))
                + p * max(abs(cell[0] - cop[0]), abs(cell[1] - cop[1]))
                for cop, p in probs.items()
            )

        def expected_chebyshev(cell: Coord) -> float:
            return sum(
                p * max(abs(cell[0] - cop[0]), abs(cell[1] - cop[1])) for cop, p in probs.items()
            )

        def score(move: str) -> float:
            dest = board.apply_move(observation.position, move)
            value = opts["w_cop_distance"] * expected_flight(dest)
            value += opts["w_mobility"] * len(legal_moves(board, dest, observation.move_set))
            value += opts["w_region"] * region_size(
                board, dest, observation.move_set, int(opts["region_cap"]), cache
            )
            if move == STAY and expected_chebyshev(dest) <= opts["stay_penalty_radius"]:
                value -= opts["stay_penalty"]
            return value

        return max(candidates, key=lambda m: (score(m), m))
