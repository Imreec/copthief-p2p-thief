"""Local mini-game runner (PLAN §13 M1, fake-transport half): the loop the CLI will call.

Wires two symmetric PeerSessions through the in-process MCP fake — every exchange goes
through a tool call, exactly as it will over FastMCP — and settles the game with the
mutual audit. Deterministic: seeds fix the walks, step indices serve as timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from copthief_core.domain.state_machine import GameState
from copthief_core.infra.fake_mcp import FakeMcpClient, FakeMcpServer
from copthief_core.peer.audit_flow import (
    build_audit,
    derive_result,
    handle_submit_audit,
    verify_audit,
)
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all
from copthief_core.shared.jsonl_logger import JsonlEventLogger
from copthief_core.wire.audit import AuditPayload


@dataclass(frozen=True)
class MatchResult:
    """Everything the M1 exit criterion asks to observe about one local mini-game."""

    outcome: str
    steps: int
    survival_threshold: int
    game_uid: str
    audit_ok_police_side: bool
    audit_ok_thief_side: bool
    police_state: GameState
    thief_state: GameState
    scores: tuple[int, int]
    survival_cop_points: int
    survival_thief_points: int
    police_moves: tuple[str, ...]
    thief_moves: tuple[str, ...]


def _server_for(session: PeerSession) -> FakeMcpServer:
    """The four peer tools, exposed exactly as the FastMCP server will expose them."""
    return FakeMcpServer(
        tools={
            "negotiate": session.handle_negotiate,
            "receive_turn": session.handle_receive_turn,
            "submit_audit": lambda raw: handle_submit_audit(session, raw),
            "receive_control": session.handle_receive_control,
        }
    )


def run_local_minigame(
    config_dir: Path, *, police_seed: int, thief_seed: int, log_path: Path | None = None
) -> MatchResult:
    """One full mini-game: handshake → turns to survival → mutual audit (Input: the
    config tree + seeds + optional JSONL log path; Output: the observed MatchResult).

    With `log_path`, every exchanged payload is logged verbatim (PLAN §7) so the game
    replays and re-verifies from the log alone (peer/replay, M1-8)."""
    log = JsonlEventLogger(log_path).log if log_path is not None else (lambda event: None)
    constitution, private, _limits = load_all(config_dir, counted=False)
    police = PeerSession(constitution, private, role="police", seed=police_seed)
    thief = PeerSession(constitution, private, role="thief", seed=thief_seed)
    to_thief = FakeMcpClient(_server_for(thief))
    to_police = FakeMcpClient(_server_for(police))
    log({"event": "provenance", "payload": {"police_seed": police_seed, "thief_seed": thief_seed}})

    for sender, client, payload in (
        ("police", to_thief, police.negotiate_payload()),
        ("thief", to_police, thief.negotiate_payload()),
    ):
        log({"event": "negotiate", "sender": sender, "payload": payload})
        client.call("negotiate", payload)

    threshold = constitution.movement.survival_threshold
    for step in range(1, threshold + 1):
        for sender, client, session in (("police", to_thief, police), ("thief", to_police, thief)):
            message = session.take_turn(now=float(step) if sender == "police" else step + 0.5)
            log({"event": "turn", "sender": sender, "message": message})
            client.call("receive_turn", message)
        log(
            {
                "event": "state",
                "police": police.machine.state.value,
                "thief": thief.machine.state.value,
            }
        )

    police_claim = {
        "result": derive_result(
            steps_survived=len(police.records),
            survival_threshold=threshold,
            max_moves=constitution.movement.max_moves,
        ),
        "steps": len(police.records),
    }
    police_audit = build_audit(police.role, police.records, police_claim)
    log({"event": "audit", "payload": police_audit})
    settlement = to_thief.call("submit_audit", police_audit)
    log({"event": "audit_answer", "payload": settlement})
    thief_side_ok = settlement["status"] == "verified"
    police_side_ok = verify_audit(AuditPayload.from_wire(settlement["audit"])) == []

    outcome = str(police_claim["result"])
    scoring = constitution.scoring
    scores = (
        (scoring.survival_cop, scoring.survival_thief) if outcome == "thief_survival" else (0, 0)
    )
    log(
        {
            "event": "result",
            "payload": {
                "outcome": outcome,
                "steps": len(police.records),
                "game_uid": police.game_uid or "",
                "audit_ok_police_side": police_side_ok,
                "audit_ok_thief_side": thief_side_ok,
            },
        }
    )
    return MatchResult(
        outcome=outcome,
        steps=len(police.records),
        survival_threshold=threshold,
        game_uid=police.game_uid or "",
        audit_ok_police_side=police_side_ok,
        audit_ok_thief_side=thief_side_ok,
        police_state=police.machine.state,
        thief_state=thief.machine.state,
        scores=scores,
        survival_cop_points=scoring.survival_cop,
        survival_thief_points=scoring.survival_thief,
        police_moves=tuple(str(r.payload["move"]) for r in police.records),
        thief_moves=tuple(str(r.payload["move"]) for r in thief.records),
    )
