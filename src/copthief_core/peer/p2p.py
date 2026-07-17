"""Two-process localhost match (PLAN §13 M1 exit): the initiator-side driving loop.

The police process drives: negotiate → turns → audit, all through the opponent's MCP
endpoint; the thief process only serves its tools (infra.mcp_server). Deterministic
apart from wall-clock timestamps. The subprocess spawn/teardown lives in the sdk.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from copthief_core.peer.audit_flow import build_audit, derive_result, verify_audit
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all
from copthief_core.wire.audit import AuditPayload


class ToolClient(Protocol):
    """The transport surface (real McpToolClient or the in-process fake client)."""

    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class P2PMatchResult:
    """What the initiator side can observe and prove about a two-process mini-game."""

    outcome: str
    steps: int
    game_uid: str
    audit_ok_police_side: bool
    audit_ok_thief_side: bool
    scores: tuple[int, int]


def drive_match(config_dir: Path, client: ToolClient, *, police_seed: int) -> P2PMatchResult:
    """Play one full mini-game as the police initiator against a served thief peer."""
    constitution, private, _limits = load_all(config_dir, counted=False)
    police = PeerSession(constitution, private, role="police", seed=police_seed)

    settlement = client.call("negotiate", police.negotiate_payload())
    police.handle_negotiate(settlement["peer"])

    threshold = constitution.movement.survival_threshold
    for _step in range(1, threshold + 1):
        response = client.call("receive_turn", police.take_turn(now=time.time()))
        police.handle_receive_turn(response["turn"])

    claim = {
        "result": derive_result(
            steps_survived=len(police.records),
            survival_threshold=threshold,
            max_moves=constitution.movement.max_moves,
        ),
        "steps": len(police.records),
    }
    audit_answer = client.call("submit_audit", build_audit(police.role, police.records, claim))
    thief_side_ok = audit_answer["status"] == "verified"
    police_side_ok = verify_audit(AuditPayload.from_wire(audit_answer["audit"])) == []

    outcome = str(claim["result"])
    scoring = constitution.scoring
    scores = (
        (scoring.survival_cop, scoring.survival_thief) if outcome == "thief_survival" else (0, 0)
    )
    return P2PMatchResult(
        outcome=outcome,
        steps=len(police.records),
        game_uid=police.game_uid or "",
        audit_ok_police_side=police_side_ok,
        audit_ok_thief_side=thief_side_ok,
        scores=scores,
    )
