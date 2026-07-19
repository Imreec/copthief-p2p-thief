"""Post-audit opponent profiling (TODO M5-5; PLAN §8 audit tail + PRD_police_brain §6).

The audit reveals the opponent's sealed truth: intent labels (truth/lie — reference
constants) and the actual move trail. Profiling turns that into a lie-rate and a
motion prior for the NEXT mini-game; the only knob it moves is config-owned trust
(hint trust, floored — distrust-but-never-eliminate). Scent honesty is deliberately
NOT profiled: grids are never sealed (SQ3), so the audit gives no ground truth.
"""

from copthief_core.peer.audit_flow import build_audit
from copthief_core.peer.sealing import seal_turn
from copthief_core.strategy.hints import VERDICT_LIE, VERDICT_TRUTH
from copthief_core.strategy.profiling import (
    OpponentProfile,
    merge_profiles,
    profile_records,
    shifted_hint_trust,
)


def _sealed(step: int, *, intent: str, move: str = "N") -> dict:  # type: ignore[type-arg]
    record = seal_turn(
        step=step,
        grid_size=7,
        position=(step % 7, 3),
        barriers=frozenset(),
        move=move,
        intent=intent,
        hint="A canned line.",
    )
    return {"payload": record.payload, "nonce": record.nonce, "commit": record.commit}


def test_profile_counts_lies_and_moves_from_revealed_records() -> None:
    records = [
        _sealed(1, intent=VERDICT_TRUTH, move="N"),
        _sealed(2, intent=VERDICT_LIE, move="N"),
        _sealed(3, intent=VERDICT_TRUTH, move="E"),
        _sealed(4, intent=VERDICT_LIE, move="STAY"),
    ]
    profile = profile_records(records)
    assert profile.games == 1
    assert profile.hints == 4
    assert profile.lies == 2
    assert profile.lie_rate == 0.5
    assert profile.moves == {"N": 2, "E": 1, "STAY": 1}
    assert profile.motion_prior["N"] == 0.5


def test_step0_spec_records_stay_out_of_the_profile() -> None:
    spec = _sealed(0, intent=VERDICT_TRUTH)
    profile = profile_records([spec, _sealed(1, intent=VERDICT_LIE)])
    assert profile.hints == 1
    assert profile.lie_rate == 1.0


def test_profiles_merge_across_mini_games() -> None:
    first = profile_records([_sealed(1, intent=VERDICT_LIE, move="N")])
    second = profile_records([_sealed(1, intent=VERDICT_TRUTH, move="S")])
    merged = merge_profiles(first, second)
    assert merged.games == 2
    assert merged.hints == 2
    assert merged.lie_rate == 0.5
    assert merged.moves == {"N": 1, "S": 1}


def test_empty_profile_shifts_nothing() -> None:
    profile = OpponentProfile(games=0, hints=0, lies=0, moves={})
    assert profile.lie_rate == 0.0
    assert profile.motion_prior == {}
    assert shifted_hint_trust(profile, base=1.0, floor=0.2) == 1.0


def test_shifted_trust_scales_with_lie_rate_and_never_hits_zero() -> None:
    half_liar = OpponentProfile(games=1, hints=4, lies=2, moves={})
    assert shifted_hint_trust(half_liar, base=1.0, floor=0.2) == 0.5
    always_liar = OpponentProfile(games=1, hints=4, lies=4, moves={})
    # Distrust-but-never-eliminate (SQ3 stance): the floor keeps hints admissible.
    assert shifted_hint_trust(always_liar, base=1.0, floor=0.2) == 0.2


def test_profile_reads_the_audit_wire_shape() -> None:
    sealed = [
        seal_turn(
            step=s,
            grid_size=7,
            position=(s, 3),
            barriers=frozenset(),
            move="S",
            intent=VERDICT_LIE,
            hint="Decoy line.",
        )
        for s in (1, 2)
    ]
    wire = build_audit("thief", sealed, "capture")
    profile = profile_records(wire["records"])
    assert (profile.hints, profile.lies) == (2, 2)
