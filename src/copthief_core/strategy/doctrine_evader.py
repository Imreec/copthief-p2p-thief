"""DoctrineEvaderBrain (M9-3/M9-4) — survival doctrine over the belief.

The thief the counted 30–90 said we needed: it walked to the deepest corner,
camped, and was sealed by two walls it watched being built. Score order, one
lexicographic tuple (studied from anrbj666's shipped doctrine after that loss,
re-implemented and re-measured here):

1. LETHAL GATE — a landing that any plausible cop cell can end next turn
   (step-on, rule-46 wall, rule-47 imprisoning wall) ranks below everything
   else. Above flight on purpose: inside a forming seal, "away from the cop"
   is measured the long way round and walks into the wall. Belief-native MIN
   over the top-k support — a lone stale argmax dodges phantom walls and walks
   into real ones (their measured lag-1 collapse).
2. STAY CAP — after `stay_cap_limit` consecutive STAYs, STAY ranks below any
   surviving move: a camper is a self-refreshing beacon (every fresh-peak
   reader — uoh-sqak fields one — reads a camper's cell exactly).
3. CAPPED FLIGHT — expected Manhattan+Chebyshev distance from the posterior,
   capped at `safe_distance` so the forecast governs once safe; the cap lifts
   to `flee_cap_hunted` only when belief mass sits within `hunted_radius` of
   US (the fresh_flee lesson: react to threat near us, not near the rival).
4. WORST-WALL FORECAST — elementwise-MIN (escapes, region) over the support
   (wall_forecast), then destination mobility.

`DEFAULT_OPTIONS` is a data table (features.py pattern); arena `brain_options`
or `[strategy.thief]` overrides any knob.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.wall_forecast import lethal_landing, worst_wall_outcome

__all__ = ["DEFAULT_OPTIONS", "DoctrineEvaderBrain"]

DEFAULT_OPTIONS: dict[str, float] = {
    "forecast_top_k": 3.0,  # support cells the gate/forecast must survive
    "support_mass_floor": 0.05,  # ignore tail cells below this mass
    "region_cap": 24.0,  # BFS early-exit: beyond this a region counts as "open"
    "safe_distance": 3.0,  # flight cap while unhunted (forecast governs beyond)
    "flee_cap_hunted": 6.0,  # lifted flight cap while hunted
    "hunted_radius": 4.0,  # Manhattan radius around US that defines "hunted"
    "hunted_mass": 0.5,  # belief mass inside the radius that arms the lift
    "stay_cap_limit": 2.0,  # consecutive STAYs before STAY ranks last
}


class DoctrineEvaderBrain(BrainBase):
    """Lethal gate > stay cap > capped flight > worst-wall forecast.

    Input:  the observation and the belief over the cop; Output: one move.
    Deterministic given (seed, config): ties break on the sorted move order.
    """

    _stay_run: int = 0

    def _support(self, belief: BeliefFilter, opts: dict[str, float]) -> list[Coord]:
        """The top-k believed cop cells above the mass floor (never empty)."""
        ranked = sorted(belief.probs().items(), key=lambda kv: (-kv[1], kv[0]))
        cells = [cell for cell, p in ranked if p >= opts["support_mass_floor"]]
        return (cells or [ranked[0][0]])[: int(opts["forecast_top_k"])]

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        opts = {**DEFAULT_OPTIONS, **self._options}
        board, position = observation.board, observation.position
        candidates = sorted(legal_moves(board, position, observation.move_set))
        if not candidates:
            return STAY
        probs = belief.probs()
        support = self._support(belief, opts)
        if observation.max_barriers > 0:
            quota_left = max(0, observation.max_barriers - len(board.barriers))
        else:
            quota_left = 1  # legacy caller: assume the cop can still wall
        hunted = (
            sum(
                p
                for cop, p in probs.items()
                if abs(cop[0] - position[0]) + abs(cop[1] - position[1]) <= opts["hunted_radius"]
            )
            >= opts["hunted_mass"]
        )
        flee_cap = opts["flee_cap_hunted"] if hunted else opts["safe_distance"]

        def flight(cell: Coord) -> float:
            """Expected Manhattan+Chebyshev separation (the M7-14 evader form)."""
            return sum(
                p * (abs(cell[0] - cop[0]) + abs(cell[1] - cop[1]))
                + p * max(abs(cell[0] - cop[0]), abs(cell[1] - cop[1]))
                for cop, p in probs.items()
            )

        def score(move: str) -> tuple[float, ...]:
            dest = board.apply_move(position, move)
            lethal = lethal_landing(board, dest, support, quota_left=quota_left)
            stay_ok = 0.0 if move == STAY and self._stay_run >= opts["stay_cap_limit"] else 1.0
            outcomes = [
                worst_wall_outcome(
                    board,
                    dest,
                    cop,
                    observation.move_set,
                    region_cap=int(opts["region_cap"]),
                    quota_left=quota_left,
                )
                for cop in support
            ]
            worst_escapes = min(escapes for escapes, _ in outcomes)
            # Clamp at the cap: the capped BFS may overshoot by frontier-order noise,
            # and "beyond the cap" MEANS open — noise must not break genuine ties.
            worst_region = min(int(opts["region_cap"]), min(region for _, region in outcomes))
            mobility = len(legal_moves(board, dest, observation.move_set))
            return (
                0.0 if lethal else 1.0,
                stay_ok,
                min(flight(dest), flee_cap),
                float(worst_escapes),
                float(worst_region),
                float(mobility),
            )

        # M9-5: exact ties resolve by the seeded shuffle (sub-game seeds differ, so a
        # rival cannot replay our path), with STAY last in any tie — a tied STAY is
        # a free beacon. Same (config, seed) still replays identically.
        self._rng.shuffle(candidates)
        best = max(candidates, key=lambda m: (score(m), m != STAY))
        self._stay_run = self._stay_run + 1 if best == STAY else 0
        return best
