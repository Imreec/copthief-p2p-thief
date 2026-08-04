"""M7-34: the final_result league fields (book §9.2.1 + the attached example).

The book's example result carries three league-standing inputs our artifact lacked:
`games_played_including_this` (the rules-37/38 mutual game-count declarations),
`first_meeting_between_groups`, and `diversity_reward_applied` — the App F diversity
reward (10, fixed) goes to the WINNER of a first counted meeting ("ניקוד על ניצחון
מול יריבה חדשה"). Warm-ups are never counted, so a friendly emits counts without the
+1 and never applies the reward. Each side's own count comes from its declaration
(`counted_games_played`, now also in our handshake identity — the opponent team
already sends theirs); the opponent's rides their captured identity.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from report_fixtures import make_identity, make_summary

from copthief_core.domain.scoring import ScoringTable
from copthief_core.report.emit import emit_series
from copthief_core.report.series_from_logs import opponent_identity_from_logs
from copthief_core.sdk.identity import identity_block
from copthief_core.shared.config import load_all

_CONSTITUTION, SHIPPED, _LIMITS = load_all(Path("config"), counted=False)


def _emit(
    tmp_path: Path,
    table: ScoringTable,
    shared_terms: dict[str, Any],
    *,
    counted: bool = False,
    first_meeting: bool = True,
    own_prior: int = 0,
    opp_prior: int | None = None,
) -> dict[str, Any]:
    own = make_identity("team-a", 8801)
    own["counted_games_played"] = own_prior
    opp = make_identity("team-b", 8802)
    if opp_prior is not None:
        opp["counted_games_played"] = opp_prior
    return emit_series(
        summaries=[
            make_summary(sub_game_number=1, role="thief", result="capture", winner="police"),
        ],
        own_identity=own,
        opponent_identity=opp,
        game_id="team-a-vs-team-b",
        game_uid="uid-1",
        shared_terms=shared_terms,
        terms={"rules": {"max_steps": 35}},
        table=table,
        out_root=tmp_path,
        counted=counted,
        first_meeting=first_meeting,
    )


def test_a_friendly_counts_no_game_and_applies_no_reward(
    tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]
) -> None:
    final = _emit(tmp_path, table, shared_terms)["final_result"]
    assert final["games_played_including_this"] == {"team-a": 0, "team-b": 0}
    assert final["first_meeting_between_groups"] is True
    assert final["diversity_reward_applied"] == {"team-a": False, "team-b": False}


def test_a_counted_first_meeting_rewards_the_winner_only(
    tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]
) -> None:
    # team-b wins the single sub-game (capture as police in the fixture summary).
    final = _emit(tmp_path, table, shared_terms, counted=True, own_prior=2, opp_prior=3)[
        "final_result"
    ]
    assert final["games_played_including_this"] == {"team-a": 3, "team-b": 4}
    assert final["first_meeting_between_groups"] is True
    assert final["diversity_reward_applied"] == {"team-a": False, "team-b": True}


def test_a_counted_repeat_meeting_applies_no_reward(
    tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]
) -> None:
    final = _emit(tmp_path, table, shared_terms, counted=True, first_meeting=False)["final_result"]
    assert final["first_meeting_between_groups"] is False
    assert final["diversity_reward_applied"] == {"team-a": False, "team-b": False}


def test_our_identity_block_declares_the_counted_game_count() -> None:
    block = identity_block(SHIPPED)
    # What rules 37-38 require is that the DECLARED count equals what we actually
    # carry — never a literal, which changes after every counted series (M7-41).
    assert block["counted_games_played"] == SHIPPED.counted_games_played


def test_opponent_identity_capture_passes_the_declared_count_through(
    tmp_path: Path,
) -> None:
    log = tmp_path / "g01.jsonl"
    event = {
        "event": "agreement_received",
        "raw": {"identity": {"group_id": "team-b", "counted_games_played": 4}},
    }
    log.write_text(json.dumps(event) + "\n", encoding="utf-8", newline="\n")
    captured = opponent_identity_from_logs([log], "team-b")
    assert captured["counted_games_played"] == 4
    bare = tmp_path / "g02.jsonl"
    bare.write_text(
        json.dumps({"event": "agreement_received", "raw": {"identity": {"group_id": "x"}}}) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    assert opponent_identity_from_logs([bare], "x").get("counted_games_played") is None


def test_private_settings_carry_a_coherent_league_ledger() -> None:
    """The ledger is LIVE state, not a constant: it advances after every counted series
    (M7-41 set it to 1/["anrbj666"] the night the first counted game was played), and it
    differs per repo. So this pins the INVARIANTS a false declaration would break —
    rules 37-38 — rather than today's values, which would go red in the sibling and
    again after every counted game (gotcha #9)."""
    assert isinstance(SHIPPED.counted_games_played, int)
    assert SHIPPED.counted_games_played >= 0
    assert isinstance(SHIPPED.counted_opponents, tuple)
    # One counted game per opponent (book §9.2.1), so the names cannot repeat, and the
    # count can never be smaller than the number of distinct opponents played.
    assert len(set(SHIPPED.counted_opponents)) == len(SHIPPED.counted_opponents)
    assert SHIPPED.counted_games_played >= len(SHIPPED.counted_opponents)


def test_opponent_identity_reads_the_declaration_shaped_hardware_key(
    tmp_path: Path,
) -> None:
    """M7-38 (the 16:00 nulls, solved): their identity ships `hardware_spec` in the
    book-attached declaration shape; ours ships `spec` in the reference F8b shape.
    The reader accepts both — declaration-shaped keys are remapped to the sysinfo
    names downstream expects (gpu_model -> gpu_type), so their real values reach our
    declaration instead of nulls. Never invented: absent stays empty."""
    log = tmp_path / "g01.jsonl"
    event = {
        "event": "agreement_received",
        "raw": {
            "identity": {
                "group_id": "team-b",
                "hardware_spec": {
                    "cpu_type": "TestCPU",
                    "cpu_freq_mhz": 3418,
                    "cpu_cores": 24,
                    "ram_gb": 32,
                    "gpu_model": "TestGPU",
                    "vram_gb": 24,
                },
            }
        },
    }
    log.write_text(json.dumps(event) + "\n", encoding="utf-8", newline="\n")
    captured = opponent_identity_from_logs([log], "team-b")
    assert captured["spec"]["gpu_type"] == "TestGPU"
    assert captured["spec"]["cpu_freq_mhz"] == 3418
    assert captured["spec"]["vram_gb"] == 24
