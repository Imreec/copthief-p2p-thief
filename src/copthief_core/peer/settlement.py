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

    def result(*, audit_ok: bool, claim: str, problems: tuple[str, ...]) -> PeerGameResult:
        return PeerGameResult(
            role=session.role,
            outcome=outcome,
            steps=steps,
            game_uid=uid,
            audit_ok=audit_ok,
            opponent_claim=claim,
            problems=problems,
        )

    if session.machine.state is not GameState.GAME_OVER:
        return result(audit_ok=False, claim="", problems=(f"audit skipped: {outcome}",))
    ours = build_audit(session.role, session.records, wire_result(outcome))
    emit({"event": "audit", "payload": ours})
    theirs = transport.exchange_audit(ours)
    if theirs is not None:
        events.inbound(emit, "audit_received", session.role, theirs)
    if theirs is None:
        return result(audit_ok=False, claim="", problems=("no audit received from opponent",))
    claim, problems = validate_opponent_audit(
        theirs, survival_threshold=session.constitution.movement.survival_threshold
    )
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
    return result(audit_ok=not problems, claim=claim, problems=tuple(problems))
