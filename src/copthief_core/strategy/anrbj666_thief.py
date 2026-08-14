"""anrbj666's FIELDED thief as an arena arm (M11 part 2) — their HEAD `f95b438`.

Re-implemented from behavior in the repos anrbj666 shared for study (ADR-0011
consent basis; no code copied). Models their fielded stack's ranking law:

- BLIND (peak mass under `trust_mass`): lethal gate over the top-k support
  (a landing any support cell can end next turn ranks last), then ROOM —
  `min(openness, safe_exits)` — above distance (their 8feb6ad "imprisonment is
  capture"), then worst-wall escapes/region MIN over the support, then raw
  distance. Their fresh-flee: when the believed cop is within `fresh_radius`,
  capped distance REPLACES the room term (the state their corner death lived in).
- TRUSTED (peak mass >= `trust_mass`, their 0.75 gate — the trail-head-pin
  regime): adjacency-avoidance first (`min(d, 2)`), then the worst-wall
  outcome against the peak, then edge aversion, distance, openness.
- STAY wins exact ties (their incumbent rule), moves shuffle seeded among equals.

Fidelity caveats: their survival CERTIFICATE is not modeled (their own keep-gate
measured survival identical with it off) and the stealth/self-mirror term is
dropped (needs a transmitted-trail mirror; it is a tie-shaper at weight 8 on a
score in the hundreds). Their fresh signal reads our transmitted trail; the
believed-cop-distance proxy stands in for it here.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.region import path_length
from copthief_core.strategy.wall_forecast import worst_wall_outcome

__all__ = ["ANRBJ666_THIEF_DEFAULTS", "Anrbj666ThiefBrain"]

ANRBJ666_THIEF_DEFAULTS: dict[str, float] = {
    "trust_mass": 0.75,  # their SHARP_BELIEF: at this peak mass, play as if exact
    "support_top_k": 3.0,  # forecast/gate support size
    "support_mass_floor": 0.05,  # their support_mass_threshold
    "safe_exits": 3.0,  # their SAFE_EXITS room clamp
    "fresh_radius": 4.0,  # their fresh_alert_radius (proxy: believed cop distance)
    "fresh_flee_cap": 6.0,  # their min(d, 2*safe_distance) flight cap when fresh
    "region_cap": 49.0,  # their reachable-region scan is uncapped on a 7x7
}


class Anrbj666ThiefBrain(BrainBase):
    """Room-first blind survival with the 0.75 trusted flip (their fielded thief).

    Input:  the observation and the belief over the cop (feed `sharp199`).
    Output: one move; STAY wins exact ties, seeded shuffle among tied moves.
    """

    def _support(self, belief: BeliefFilter, opts: dict[str, float]) -> list[Coord]:
        ranked = sorted(belief.probs().items(), key=lambda kv: (-kv[1], kv[0]))
        cells = [cell for cell, p in ranked if p >= opts["support_mass_floor"]]
        return (cells or [ranked[0][0]])[: int(opts["support_top_k"])]

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        opts = {**ANRBJ666_THIEF_DEFAULTS, **self._options}
        board, position = observation.board, observation.position
        candidates = sorted(legal_moves(board, position, observation.move_set))
        if not candidates:
            return STAY
        peak = belief.argmax()
        trusted = belief.probs().get(peak, 0.0) >= opts["trust_mass"]
        if observation.max_barriers > 0:
            quota_left = max(0, observation.max_barriers - len(board.barriers))
        else:
            quota_left = 1
        support = self._support(belief, opts)
        cap = int(opts["region_cap"])
        low = board.axis_start_index
        high = low + board.grid_size - 1

        def dist(cell: Coord) -> float:
            length = path_length(board, cell, peak, observation.move_set)
            return 1e6 if length is None else float(length)

        def openness(cell: Coord) -> int:
            return sum(1 for n in board.neighbors(cell) if not board.is_blocked(n))

        def score(move: str) -> tuple[float, ...]:
            cell = board.apply_move(position, move)
            d = dist(cell)
            if trusted:
                escapes, region = worst_wall_outcome(
                    board, cell, peak, observation.move_set, region_cap=cap, quota_left=quota_left
                )
                edge = min(cell[0] - low, high - cell[0], cell[1] - low, high - cell[1])
                return (min(d, 2.0), float(escapes), float(region), float(edge), d, openness(cell))
            outcomes = [
                worst_wall_outcome(
                    board, cell, cop, observation.move_set, region_cap=cap, quota_left=quota_left
                )
                for cop in support
            ]
            worst_escapes = min(e for e, _ in outcomes)
            worst_region = min(r for _, r in outcomes)
            lethal = (worst_escapes, worst_region) == (0, 0)
            me_gap = abs(position[0] - peak[0]) + abs(position[1] - peak[1])
            fresh = me_gap <= opts["fresh_radius"] and opts["fresh_radius"] > 0.0
            room = (
                min(d, opts["fresh_flee_cap"]) if fresh else min(openness(cell), opts["safe_exits"])
            )
            return (0.0 if lethal else 1.0, room, float(worst_escapes), float(worst_region), d)

        moving = [m for m in candidates if m != STAY]
        self._rng.shuffle(moving)
        best, best_score = STAY, score(STAY) if STAY in candidates else None
        for move in moving:
            s = score(move)
            if best_score is None or s > best_score:
                best, best_score = move, s
        return best
