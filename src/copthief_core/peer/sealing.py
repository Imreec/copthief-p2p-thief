"""Turn sealing (book ch.5 §5.3; PRD_crypto §4): build the self-consistent sealed record.

The record's key set is self-only (kit §3): the opponent never reconstructs it, only
re-hashes what we reveal — so seal↔store↔reveal must be byte-identical, which is why the
record is built exactly once, here, and stored verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from copthief_core import __version__ as code_version
from copthief_core.domain.board import Coord
from copthief_core.domain.crypto import commit as crypto_commit
from copthief_core.domain.crypto import make_nonce
from copthief_core.shared.config_model import Constitution, PrivateSettings
from copthief_core.shared.locked_models import SCENT_MODEL
from copthief_core.shared.sysinfo import collect_spec, current_commit_hash


def state_string(grid_size: int, position: Coord, barriers: frozenset[Coord]) -> str:
    """The reference's exact self-state encoding, pinned by the kit vectors (kit §3).

    Micro-snippet transplant (ADR-0002 log): the format — Python list repr WITH the
    space after the comma, barriers sorted — must reproduce byte-for-byte, or our own
    revealed records would not match the form other tooling expects.
    """
    barrier_lists = sorted([list(b) for b in barriers])
    return f"grid={grid_size}x{grid_size};self={list(position)};barriers={barrier_lists}"


@dataclass(frozen=True)
class SealedTurn:
    """One sealed record: the verbatim payload, its withheld nonce, the sent commit."""

    payload: dict[str, Any]
    nonce: str
    commit: str


def seal_turn(
    *,
    step: int,
    grid_size: int,
    position: Coord,
    barriers: frozenset[Coord],
    move: str,
    intent: str,
    hint: str,
    model: str = "none",
    tokens_step: int = 0,
    tokens_total: int = 0,
    response_seconds: float = 0.0,
) -> SealedTurn:
    """Seal one turn (Input: the turn's facts; Output: record + nonce + commit).

    The nonce is fresh per record (`secrets`) and withheld until the end-of-game audit;
    only the commit travels with the TurnMessage. M6-3: model/tokens/timing are sealed
    INSIDE the record — the 0-token fairness claim becomes cryptographically auditable
    (defaults = the absent-accounting/template path, which charges 0 every step).
    """
    payload: dict[str, Any] = {
        "step": step,
        "state": state_string(grid_size, position, barriers),
        "position": list(position),
        "move": move,
        "intent": intent,
        "hint": hint,
        "model": model,
        "tokens_step": tokens_step,
        "tokens_total": tokens_total,
        "response_seconds": response_seconds,
    }
    nonce = make_nonce()
    return SealedTurn(payload=payload, nonce=nonce, commit=crypto_commit(payload, nonce))


def seal_spec_record(
    *,
    spec: dict[str, Any],
    model: str,
    group_name: str,
    sub_game_number: int,
    github_commit: str,
    num_games_declared: int,
    scent_model_sha256: str,
) -> SealedTurn:
    """The sealed step-0 system_spec declaration (book §6/§8; PRD_reporting §4).

    Seals hardware + model + code version + the EXACT commit hash played + the
    truthful game-count (rules 37–38). Lives BESIDE the game records — the audit
    prepends it; step numbering and settlement math never see it. (The reference's
    log `_schema` promises github_commit here but its code omits it — we close that
    gap on our side; sealed payloads are self-consistent per side.)
    """
    payload: dict[str, Any] = {
        "step": 0,
        "type": "system_spec",
        "spec": spec,
        "model": model,
        "code_version": code_version,
        "group_name": group_name,
        "sub_game_number": sub_game_number,
        "github_commit": github_commit,
        "num_games_declared": num_games_declared,
        # M3-8 (ADR-0004 v2 decision 4): the locked model becomes TAMPER-EVIDENT here.
        # The signed 14-key terms cannot carry it — the key set is reference-frozen and
        # adding a key breaks the terms signature against every reference-derived peer —
        # so the step-0 commit chain is where the declaration binds.
        "scent_model_sha256": scent_model_sha256,
    }
    nonce = make_nonce()
    return SealedTurn(payload=payload, nonce=nonce, commit=crypto_commit(payload, nonce))


def live_spec_record(
    private: PrivateSettings, constitution: Constitution, *, sub_game_number: int | None = None
) -> SealedTurn:
    """The real host's step-0 record: probed spec + this checkout's HEAD + the signed
    game-count. `sub_game_number` overrides the TOML value in a series (M6-6)."""
    return seal_spec_record(
        spec=collect_spec(),
        model=private.llm_model,
        group_name=private.group_name,
        sub_game_number=private.sub_game_number if sub_game_number is None else sub_game_number,
        github_commit=current_commit_hash(),
        num_games_declared=constitution.league.num_games,
        scent_model_sha256=private.locked_models.hash(SCENT_MODEL, private.scent_model),
    )
