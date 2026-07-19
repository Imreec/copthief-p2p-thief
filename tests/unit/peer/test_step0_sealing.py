"""M6-3: the sealed step-0 declaration + per-step token accounting (PRD_reporting §4).

The step-0 system_spec record seals the REAL commit hash + the truthful game-count
(rules 37–38) and lives BESIDE the game records (step numbering and settlement math
never see it); the audit prepends it. Every game turn now seals model/tokens/timing —
the fields that make the 0-token claim cryptographically auditable (M6-8).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import copthief_core
from copthief_core.domain.crypto import verify
from copthief_core.domain.state_machine import GameState
from copthief_core.peer.sealing import (
    SealedTurn,
    live_spec_record,
    seal_spec_record,
    seal_turn,
)
from copthief_core.peer.session import PeerSession
from copthief_core.peer.settlement import settle
from copthief_core.shared.config import load_all
from copthief_core.shared.sysinfo import current_commit_hash

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)
PRIVATE = replace(_SHIPPED, police_class="random", thief_class="random")

SPEC = {"os": "TestOS", "cpu_type": "TestCPU"}


def _spec_record() -> SealedTurn:
    return seal_spec_record(
        spec=SPEC,
        model="none",
        group_name="Team-A",
        sub_game_number=1,
        github_commit="ab" * 20,
        num_games_declared=2,
    )


def test_spec_record_seals_the_declaration_key_set() -> None:
    record = _spec_record()
    assert set(record.payload) == {
        "step",
        "type",
        "spec",
        "model",
        "code_version",
        "group_name",
        "sub_game_number",
        "github_commit",
        "num_games_declared",
    }
    assert record.payload["step"] == 0
    assert record.payload["type"] == "system_spec"
    assert record.payload["code_version"] == copthief_core.__version__
    assert record.payload["github_commit"] == "ab" * 20
    assert record.payload["num_games_declared"] == 2
    assert verify(record.payload, record.nonce, record.commit)


def test_live_spec_record_declares_the_real_head_and_signed_game_count() -> None:
    record = live_spec_record(PRIVATE, CONSTITUTION, sub_game_number=3)
    assert record.payload["github_commit"] == current_commit_hash()
    assert record.payload["num_games_declared"] == CONSTITUTION.league.num_games
    assert record.payload["group_name"] == PRIVATE.group_name
    assert record.payload["model"] == PRIVATE.llm_model
    assert record.payload["sub_game_number"] == 3
    assert verify(record.payload, record.nonce, record.commit)


def test_seal_turn_seals_token_accounting_with_absent_defaults() -> None:
    sealed = seal_turn(
        step=1,
        grid_size=7,
        position=(1, 2),
        barriers=frozenset(),
        move="MOVE:S",
        intent="truth",
        hint="hi",
    )
    payload = sealed.payload
    assert payload["model"] == "none"
    assert payload["tokens_step"] == 0
    assert payload["tokens_total"] == 0
    assert payload["response_seconds"] == 0.0
    assert verify(payload, sealed.nonce, sealed.commit)


def test_take_turn_seals_the_sessions_token_accounting() -> None:
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief.handle_negotiate(police.negotiate_payload())
    thief.take_turn(now=0.0)
    payload = thief.records[-1].payload
    assert payload["model"] == PRIVATE.llm_model
    assert payload["tokens_step"] == 0
    assert payload["tokens_total"] == 0
    assert payload["response_seconds"] >= 0.0


def test_session_spec_record_fills_the_identity_spec_gap() -> None:
    """F8b closes: with a step-0 record the handshake identity carries the real spec
    dict (the opponent's declaration writer needs it); without one it stays {}."""
    record = _spec_record()
    with_spec = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1, spec_record=record)
    assert with_spec.negotiate_payload()["identity"]["spec"] == SPEC
    without = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    assert without.negotiate_payload()["identity"]["spec"] == {}


def test_settlement_audit_prepends_the_spec_record_and_keeps_step_math() -> None:
    session = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2, spec_record=_spec_record())
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    session.handle_negotiate(police.negotiate_payload())
    session.take_turn(now=0.0)
    session.outcome = "thief_survival"
    for state in (GameState.VERIFYING, GameState.GAME_OVER):
        session.machine.advance(state)

    sent: list[dict[str, Any]] = []

    class _NoAnswer:
        def exchange_audit(self, ours: dict[str, Any]) -> None:
            sent.append(ours)

    emitted: list[dict[str, Any]] = []
    result = settle(session, _NoAnswer(), emitted.append)  # type: ignore[arg-type]
    records = sent[0]["records"]
    assert records[0]["payload"]["step"] == 0
    assert records[0]["payload"]["type"] == "system_spec"
    assert records[1]["payload"]["step"] == 1
    assert result.steps == 1  # game steps only — the declaration is not a turn
