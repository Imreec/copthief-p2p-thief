"""PLAN §13 M5 exit: profiling shifts mini-game-2 priors in a test series (TODO M5-5).

Mini-game 1: a lying thief is played to capture in-process; its audit reveals the
sealed intent labels. Mini-game 2: the police session is built with the profile-shifted
hint trust — lower than the config default, never below the config floor. The belief
math itself is untouched (M3-8 boundary): only the constructor-injected trust moves.
"""

from pathlib import Path

from copthief_core.domain.belief import BeliefFilter
from copthief_core.peer.audit_flow import build_audit
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all, load_gazetteer
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision
from copthief_core.strategy.hints import VERDICT_LIE
from copthief_core.strategy.profiling import profile_records, shifted_hint_trust

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
GAZETTEER = load_gazetteer(
    Path("config") / "gazetteer.json",
    map_area=CONSTITUTION.world.map_area,
    board=CONSTITUTION.board.make_board(),
)


class _LiarBrain(BrainBase):
    """Stays put and lies every turn (the deception mechanism, timing forced ON)."""

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        return "STAY"

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        decoy = observation.gazetteer.landmarks()[-1] if observation.gazetteer else None
        return Decision(move="STAY", hint_verdict=VERDICT_LIE, hint_landmark=decoy)


def _play_capture_series() -> tuple[PeerSession, PeerSession]:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1, gazetteer=GAZETTEER)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2, gazetteer=GAZETTEER)
    thief.brain = _LiarBrain(seed=2)
    thief.handle_negotiate(police.negotiate_payload())
    police.handle_negotiate(thief.negotiate_payload())
    police.handle_receive_turn(thief.take_turn(now=1.0))
    claim_turn = police.take_turn(now=1.5)
    claim_turn["capture_claim"] = list(thief.position)  # script the capture ending
    thief.handle_receive_turn(claim_turn)
    police.handle_receive_turn(thief.take_turn(now=2.0))  # the mandatory final message
    assert police.outcome == "cop_capture"
    return police, thief


def test_profiling_shifts_the_second_mini_games_hint_trust() -> None:
    _police, thief = _play_capture_series()
    revealed = build_audit("thief", thief.records, "capture")["records"]
    profile = profile_records(revealed)
    assert profile.lie_rate > 0.0  # the lie labels really are in the audit
    shifted = shifted_hint_trust(
        profile, base=PRIVATE.hint_trust_default, floor=PRIVATE.profile_hint_floor
    )
    game_one = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=3, gazetteer=GAZETTEER)
    game_two = PeerSession(
        CONSTITUTION, PRIVATE, role="police", seed=3, gazetteer=GAZETTEER, hint_trust=shifted
    )
    assert game_two.hint_trust == shifted
    assert game_two.hint_trust < game_one.hint_trust  # the M5 exit: priors moved
    assert game_two.hint_trust >= PRIVATE.profile_hint_floor


def test_verified_audit_emits_the_profile_event_in_the_peer_loop() -> None:
    # The settlement tail: a VERIFIED opponent audit produces a `profile` event
    # carrying the lie-rate and the config-floored next-game hint trust.
    import threading
    from dataclasses import replace

    from copthief_core.peer.p2p import run_peer_game
    from copthief_core.peer.transport import queue_pair

    pinned = replace(PRIVATE, police_class="random", thief_class="random")
    police = PeerSession(CONSTITUTION, pinned, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, pinned, role="thief", seed=2)
    police_t, thief_t = queue_pair(wait_timeout=PRIVATE.connect_timeout_seconds)
    police_events: list[dict] = []  # type: ignore[type-arg]

    def play(session: PeerSession, transport, log) -> None:  # noqa: ANN001 - Protocol param
        run_peer_game(
            session,
            transport,
            turn_timeout=PRIVATE.turn_timeout_seconds,
            poll_interval=PRIVATE.poll_interval_seconds,
            log=log,
        )

    threads = [
        threading.Thread(target=play, args=(police, police_t, police_events.append)),
        threading.Thread(target=play, args=(thief, thief_t, lambda e: None)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=PRIVATE.turn_timeout_seconds)
    profiles = [e for e in police_events if e["event"] == "profile"]
    assert len(profiles) == 1
    payload = profiles[0]["payload"]
    assert payload["hints"] == payload["games"] * CONSTITUTION.movement.survival_threshold
    assert 0.0 <= payload["lie_rate"] <= 1.0
    assert payload["next_hint_trust"] >= PRIVATE.profile_hint_floor
    assert abs(sum(payload["motion_prior"].values()) - 1.0) < 1e-9


def test_final_caught_message_counts_as_a_truthful_hint() -> None:
    _police, thief = _play_capture_series()
    profile = profile_records(build_audit("thief", thief.records, "capture")["records"])
    # The liar lied on its game turn; the mandatory final message seals truth.
    assert profile.hints == 2
    assert profile.lies == 1
