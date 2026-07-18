"""ThiefBrain (TODO M5-3; PRD_thief_brain §3) — ⚑ the thief repo's graded core.

Region-survival move policy + articulation trap-awareness + deception timing over the
belief's public read surface and the M5-3 hint-intent seam. Deterministic given
(config, seed): the RNG is interface-only, ties break on sorted move order. No LLM
anywhere in this package (App E rule 25 — pinned by an AST-scan test).
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision
from copthief_core.strategy.hints import VERDICT_LIE
from copthief_thief.articulation import articulation_points, min_sealed_component
from copthief_thief.deception import DeceptionClock, SelfMirror
from copthief_thief.features import resolve_options, truncated_support, worst_case_distance
from copthief_thief.regions import safe_region_size


class ThiefBrain(BrainBase):
    """Survive the clock: keep distance, keep territory, refuse pockets, lie on cue."""

    _mirror: SelfMirror | None = None
    _clock: DeceptionClock | None = None

    def __init__(self, *, seed: int, options: dict[str, float] | None = None) -> None:
        super().__init__(seed=seed, options=options)
        self._visited: set[Coord] = set()

    def _score(self, observation: Observation, belief: BeliefFilter, move: str) -> float:
        opts = resolve_options(self._options)
        board = observation.board
        dest = board.apply_move(observation.position, move)
        support = truncated_support(belief, int(opts["top_k"]))
        cap = int(opts["region_cap"])
        ramp = opts["ramp_multiplier"] if observation.step >= opts["ramp_start_step"] else 1.0
        score = opts["w_distance"] * ramp * worst_case_distance(dest, support)
        threat = belief.argmax()
        score += opts["w_region"] * safe_region_size(board, dest, threat, observation.move_set, cap)
        if observation.barriers_used < observation.max_barriers:
            cuts = articulation_points(board, observation.position, observation.move_set, cap)
            sealed = min_sealed_component(board, dest, cuts, observation.move_set, cap)
            if sealed < opts["trap_region_min"]:
                score -= opts["w_articulation"]  # a cheap seal away from imprisonment
        if dest not in self._visited:
            score += opts["w_spread"]
        return score

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        self._visited.add(observation.position)
        candidates = sorted(
            legal_moves(observation.board, observation.position, observation.move_set)
        )
        if not candidates:
            return STAY
        best_move, best_value = candidates[0], float("-inf")
        for move in candidates:
            value = self._score(observation, belief, move)
            if value > best_value:
                best_move, best_value = move, value
        return best_move

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        move = self._pick_move(observation, belief)
        if observation.gazetteer is None or observation.pheromones is None:
            return Decision(move=move)  # referee trials: no verbal layer to time
        opts = resolve_options(self._options)
        if self._mirror is None:  # first turn: the thief decides at its signed start
            self._mirror = SelfMirror(
                board=observation.board,
                move_set=observation.move_set,
                start=observation.position,
                pheromones=observation.pheromones,
                smell_trust=opts["mirror_smell_trust"],
            )
            self._clock = DeceptionClock(
                budget=int(opts["lie_budget"]), cooldown=int(opts["lie_cooldown"])
            )
        self._mirror.observe_turn(dict(observation.own_smell))
        assert self._clock is not None  # created with the mirror
        threat = belief.argmax()
        near = (
            abs(observation.position[0] - threat[0]) + abs(observation.position[1] - threat[1])
        ) <= opts["near_distance"]
        exposed = self._mirror.exposure(observation.position) >= opts["mirror_sharp_p"]
        if exposed and near and self._clock.may_lie(observation.step):
            self._clock.record_lie(observation.step)
            dest = observation.board.apply_move(observation.position, move)
            # The decoy covers the move we did NOT take: farthest landmark from our
            # actual heading (never the truthful tell for the destination).
            return Decision(
                move=move,
                hint_verdict=VERDICT_LIE,
                hint_landmark=observation.gazetteer.farthest(dest),
            )
        return Decision(move=move)
