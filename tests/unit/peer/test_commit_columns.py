"""M7-33: both `github_commit` columns, honestly (book example files, 2026-08-03).

The book's attached `4-final-result` example fills BOTH teams' commits per sub-game,
and its `3-game-log` names the step-0 record as the designed carrier ("carrying only
what changes per sub-game (github_commit)"). Our audit reveal already transmits our
step-0; this build (a) reads the OPPONENT's commit out of their revealed records at
settlement, and (b) makes our OWN value role-aware — the commit of the repo that owns
the loaded brain (the example shows commits varying across sub-games; a two-repo
team's thief games carry the thief repo's hash, not the runner's).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from copthief_core.peer.sealing import live_spec_record
from copthief_core.peer.settlement import opponent_commit
from copthief_core.shared.config import load_all
from copthief_core.shared.sysinfo import commit_for_module, current_commit_hash

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)
PRIVATE = replace(_SHIPPED, police_class="random", thief_class="random")


def _revealed(payload: dict) -> dict:
    return {"payload": payload, "nonce": "aa" * 16, "commit": "bb" * 32}


def test_opponent_commit_reads_a_system_spec_step0() -> None:
    records = [
        _revealed({"step": 0, "type": "system_spec", "github_commit": "cd" * 20}),
        _revealed({"step": 1, "move": "MOVE:N"}),
    ]
    assert opponent_commit(records) == "cd" * 20


def test_opponent_commit_reads_the_book_examples_step_zero_type_too() -> None:
    # The book's example log names the record type "step_zero"; the reference (and
    # we) use "system_spec". Read both — the field is what matters, not the label.
    records = [_revealed({"step": 0, "type": "step_zero", "github_commit": "7cf3fc9"})]
    assert opponent_commit(records) == "7cf3fc9"


def test_opponent_commit_is_unknown_without_a_step0_or_without_the_field() -> None:
    assert opponent_commit([_revealed({"step": 1, "move": "MOVE:N"})]) == "unknown"
    assert opponent_commit([_revealed({"step": 0, "type": "system_spec"})]) == "unknown"
    assert opponent_commit([]) == "unknown"


def test_commit_for_module_resolves_this_checkout_for_our_own_package() -> None:
    # copthief_core lives in THIS repo, so its module commit is this checkout's HEAD.
    assert commit_for_module("copthief_core") == current_commit_hash()


def test_commit_for_module_is_unknown_for_an_unresolvable_module() -> None:
    assert commit_for_module("no_such_package_anywhere") == "unknown"


def test_live_spec_record_is_role_aware_with_a_class_path() -> None:
    # Role-blind by construction: whatever class the config names for the role, the
    # sealed commit is that module's repo HEAD. copthief_police lives in this repo,
    # so the police role resolves to this checkout's HEAD via the module route.
    private = replace(_SHIPPED, police_class="copthief_police.brain:PoliceBrain")
    record = live_spec_record(private, CONSTITUTION, sub_game_number=1, role="police")
    assert record.payload["github_commit"] == current_commit_hash()


def test_live_spec_record_falls_back_to_the_runner_for_builtin_brains() -> None:
    # "random" is a keyword, not a module path — the runner repo's HEAD is then the
    # honest value (the stub genuinely plays from this checkout).
    record = live_spec_record(PRIVATE, CONSTITUTION, sub_game_number=1, role="thief")
    assert record.payload["github_commit"] == current_commit_hash()


def test_live_spec_record_without_a_role_keeps_the_historical_value() -> None:
    record = live_spec_record(PRIVATE, CONSTITUTION, sub_game_number=1)
    assert record.payload["github_commit"] == current_commit_hash()


def test_handshake_identity_declares_count_and_step0_commit() -> None:
    """M7-35 (Round 23): the wire identity carries the game-count declaration AND the
    commit — the opponent team's two-channel rule: negotiate declares in plaintext
    what step-0 seals, sourced FROM the sealed record so they agree by construction
    (a mismatch between a peer's own channels is itself a finding)."""
    from copthief_core.peer.sealing import live_spec_record
    from copthief_core.peer.session import PeerSession

    spec = live_spec_record(_SHIPPED, CONSTITUTION, sub_game_number=1, role="police")
    session = PeerSession(CONSTITUTION, _SHIPPED, role="police", seed=1, spec_record=spec)
    identity = session.negotiate_payload()["identity"]
    assert identity["counted_games_played"] == _SHIPPED.counted_games_played
    assert identity["github_commit"] == spec.payload["github_commit"]


def test_handshake_identity_omits_the_commit_without_a_sealed_record() -> None:
    from copthief_core.peer.session import PeerSession

    session = PeerSession(CONSTITUTION, _SHIPPED, role="thief", seed=2)
    identity = session.negotiate_payload()["identity"]
    assert "github_commit" not in identity  # never invented (dev sessions seal none)
    assert identity["counted_games_played"] == 0
