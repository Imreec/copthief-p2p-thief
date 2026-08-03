"""End-of-game settlement, split from peer/p2p (150-line rule at M5-5).

Audit exchange + verification + the M5-5 profiling tail: a VERIFIED opponent audit
is profiling evidence — the emitted `profile` event carries the lie-rate, motion
prior, and the config-floored hint trust a series runner hands the next mini-game.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from copthief_core.domain.state_machine import GameState
from copthief_core.peer import events
from copthief_core.peer.audit_flow import build_audit, verify_audit, wire_result
from copthief_core.peer.scent_check import emit_scent_physics
from copthief_core.peer.session import PeerSession
from copthief_core.peer.transport import PeerTransport
from copthief_core.strategy.profiling import profile_records, shifted_hint_trust
from copthief_core.wire.audit import AuditPayload
from copthief_core.wire.validation import WireValidationError

LogFn = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class PeerGameResult:
    """What ONE peer can honestly report about its finished mini-game."""

    role: str
    outcome: str
    steps: int
    game_uid: str
    audit_ok: bool
    opponent_claim: str
    problems: tuple[str, ...]
    # M6-6: how many revealed records the opponent's audit carried (their steps +
    # step-0) — the summary's `verified_steps` when the verification passed.
    opponent_records: int = 0
    # M7-33: the commit their revealed step-0 declared — the book's example result
    # fills BOTH columns, and the step-0 record is its designed carrier.
    opponent_github_commit: str = "unknown"


def opponent_commit(records: list[dict[str, Any]]) -> str:
    """The opponent's declared commit from their revealed records ("unknown" absent).

    Reads both step-0 spellings — our/the reference's `system_spec` and the book
    example's `step_zero` — the field is what matters, not the label.
    """
    for record in records:
        payload = record.get("payload", {})
        if isinstance(payload, dict) and payload.get("type") in ("system_spec", "step_zero"):
            value = payload.get("github_commit")
            return str(value) if value else "unknown"
    return "unknown"


def validate_opponent_audit(
    raw: dict[str, Any], *, survival_threshold: int
) -> tuple[str, list[str]]:
    """(their result claim, every problem found) — empty problems == Verified OK.

    Beyond the re-hash + continuity check, the derived-never-declared backstop: a
    "survival" claim must be backed by revealed game steps reaching the threshold.
    """
    try:
        audit = AuditPayload.from_wire(raw)
    except WireValidationError as error:
        return ("invalid", [str(error)])
    problems = verify_audit(audit)
    game_steps = [
        r.payload["step"]
        for r in audit.records
        if isinstance(r.payload.get("step"), int) and r.payload["step"] >= 1
    ]
    # Survival is the THIEF's outcome: only the thief's own audit must show the
    # surviving step count (the police ends one turn short on the inbound win claim).
    if (
        audit.result_claim == "survival"
        and audit.sender == "thief"
        and len(game_steps) < survival_threshold
    ):
        problems.append(
            f"claim 'survival' with {len(game_steps)} revealed steps "
            f"below the threshold {survival_threshold}"
        )
    return (audit.result_claim, problems)


def settle(session: PeerSession, transport: PeerTransport, emit: LogFn) -> PeerGameResult:
    """Exchange audits after GAME_OVER and verify theirs; skip on a technical ending."""
    outcome = session.outcome or "incomplete"
    steps = len(session.records)
    uid = session.game_uid or ""

    def result(
        *,
        audit_ok: bool,
        claim: str,
        problems: tuple[str, ...],
        opponent_records: int = 0,
        opponent_github_commit: str = "unknown",
    ) -> PeerGameResult:
        return PeerGameResult(
            role=session.role,
            outcome=outcome,
            steps=steps,
            game_uid=uid,
            audit_ok=audit_ok,
            opponent_claim=claim,
            problems=problems,
            opponent_records=opponent_records,
            opponent_github_commit=opponent_github_commit,
        )

    if session.machine.state is not GameState.GAME_OVER:
        return result(audit_ok=False, claim="", problems=(f"audit skipped: {outcome}",))
    # M6-3: the sealed step-0 declaration leads the audit (the reference audits its
    # own spec record the same way — M2 smoke re-verified 36/36 incl. step-0).
    full_records = [session.spec_record] if session.spec_record is not None else []
    ours = build_audit(session.role, full_records + session.records, wire_result(outcome))
    emit({"event": "audit", "payload": ours})
    theirs = transport.exchange_audit(ours)
    if theirs is not None:
        events.inbound(emit, "audit_received", session.role, theirs)
    if theirs is None:
        return result(audit_ok=False, claim="", problems=("no audit received from opponent",))
    claim, problems = validate_opponent_audit(
        theirs, survival_threshold=session.constitution.movement.survival_threshold
    )
    # M6-7 (FR-11, evidence-grade only): diff their transmitted grids against the
    # trail their revealed moves imply — a loud event, never a verdict change (SQ3).
    emit_scent_physics(session, theirs, emit)
    if not problems:  # M5-5: a VERIFIED audit is profiling evidence for the series
        profile = profile_records(theirs["records"])
        emit(
            {
                "event": "profile",
                "sender": session.role,
                "payload": {
                    "opponent": session.opponent_group,
                    "games": profile.games,
                    "hints": profile.hints,
                    "lies": profile.lies,
                    "lie_rate": profile.lie_rate,
                    "motion_prior": profile.motion_prior,
                    "next_hint_trust": shifted_hint_trust(
                        profile,
                        base=session.private.hint_trust_default,
                        floor=session.private.profile_hint_floor,
                    ),
                },
            }
        )
    emit(
        {
            "event": "peer_result",
            "sender": session.role,
            "payload": {"outcome": outcome, "steps": steps, "audit_ok": not problems},
        }
    )
    theirs_records = theirs.get("records")
    listed = theirs_records if isinstance(theirs_records, list) else []
    return result(
        audit_ok=not problems,
        claim=claim,
        problems=tuple(problems),
        opponent_records=len(listed),
        opponent_github_commit=opponent_commit(listed),
    )
