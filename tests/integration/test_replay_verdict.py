"""M4-3 replay verdict (PRD_gui_replay §5): binary, exact-string, both-sides.

Rule 19 made a permanent regression: the mutation matrix flips EVERY sealed-payload
field (plus nonce and commit) of a real game's log, one at a time, and each single
flip must turn the whole match TAMPERED — "no almost-match".
"""

import json
from pathlib import Path
from typing import Any

import pytest

from copthief_core.peer.match import run_local_minigame
from copthief_core.peer.replay import (
    VERDICT_OK,
    VERDICT_TAMPERED,
    replay_from_log,
    verdict_for,
)
from copthief_core.shared.jsonl_logger import read_events

CONFIG_DIR = Path("config")


@pytest.fixture(scope="module")
def real_log(tmp_path_factory: pytest.TempPathFactory) -> Path:
    log_path = tmp_path_factory.mktemp("logs") / "game.jsonl"
    run_local_minigame(CONFIG_DIR, police_seed=11, thief_seed=22, log_path=log_path)
    return log_path


def _police_view(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The shared local log reduced to what a real one-sided live log carries: our
    outbound events, our own audit (sender lives in its payload), and the v1.1
    inbound archives."""
    return [
        e
        for e in events
        if (e["event"] in ("turn", "negotiated", "peer_result") and e.get("sender") == "police")
        or (e["event"] == "audit" and e["payload"]["sender"] == "police")
        or (e["event"] in ("turn_received", "audit_received") and e.get("receiver") == "police")
    ]


def _rewrite(events: list[dict[str, Any]], path: Path) -> Path:
    path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False, sort_keys=True) for e in events) + "\n",
        encoding="utf-8",
    )
    return path


def test_verdict_strings_are_the_books_exact_banners(real_log: Path) -> None:
    assert VERDICT_OK == "Verified OK"
    assert VERDICT_TAMPERED == "TAMPERED"
    assert verdict_for(replay_from_log(real_log)) == VERDICT_OK


def test_replay_is_deterministic(real_log: Path) -> None:
    assert replay_from_log(real_log) == replay_from_log(real_log)


@pytest.mark.parametrize(
    "field",
    ["state", "move", "intent", "hint", "position", "step"],
)
def test_single_sealed_field_mutation_flips_to_tampered(
    real_log: Path, tmp_path: Path, field: str
) -> None:
    events = read_events(real_log)
    audit = next(e for e in events if e["event"] == "audit")
    payload = audit["payload"]["records"][1]["payload"]
    payload[field] = payload[field] + 1 if isinstance(payload[field], int) else "forged"
    mutated = _rewrite(events, tmp_path / f"mutated_{field}.jsonl")
    assert verdict_for(replay_from_log(mutated)) == VERDICT_TAMPERED


@pytest.mark.parametrize("field", ["nonce", "commit"])
def test_seal_material_mutation_flips_to_tampered(
    real_log: Path, tmp_path: Path, field: str
) -> None:
    events = read_events(real_log)
    audit = next(e for e in events if e["event"] == "audit")
    audit["payload"]["records"][1][field] = "0" * len(audit["payload"]["records"][1][field])
    mutated = _rewrite(events, tmp_path / f"mutated_{field}.jsonl")
    assert verdict_for(replay_from_log(mutated)) == VERDICT_TAMPERED


def test_one_sided_live_log_verifies_both_sides(real_log: Path, tmp_path: Path) -> None:
    # A live peer log has OUR outbound events plus the v1.1 inbound archives. The
    # verifier must re-verify the OPPONENT too: their turns from `turn_received`
    # against their revealed records from `audit_received`.
    events = read_events(real_log)
    one_sided = _rewrite(_police_view(events), tmp_path / "police_view.jsonl")
    summary = replay_from_log(one_sided)
    assert verdict_for(summary) == VERDICT_OK
    assert set(summary.moves) == {"police", "thief"}  # the opponent's side is walked too


def test_tampering_the_opponents_archived_audit_is_caught(real_log: Path, tmp_path: Path) -> None:
    events = read_events(real_log)
    police_view = _police_view(events)
    their_audit = next(e for e in police_view if e["event"] == "audit_received")
    their_audit["raw"]["records"][1]["payload"]["move"] = "forged"
    mutated = _rewrite(police_view, tmp_path / "opponent_tamper.jsonl")
    assert verdict_for(replay_from_log(mutated)) == VERDICT_TAMPERED
