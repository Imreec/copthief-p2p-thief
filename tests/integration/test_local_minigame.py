"""PLAN §13 M1 exit evidence (fake-transport half): full mini-game, sealing, self-audit pass.

Two symmetric PeerSessions play a complete mini-game through the in-process MCP fake —
all four tools exercised over the fake transport — ending in survival, with both
directions' audits re-hashed clean. The two-process localhost form of the same run
arrives with the M1-7 CLI (real FastMCP transport).
"""

from pathlib import Path

from copthief_core.domain.state_machine import GameState
from copthief_core.infra.fake_mcp import FakeMcpClient, FakeMcpServer
from copthief_core.peer.match import run_local_minigame

CONFIG_DIR = Path("config")


def test_full_minigame_over_the_fake_transport_self_audits_clean() -> None:
    result = run_local_minigame(CONFIG_DIR, police_seed=11, thief_seed=22)
    assert result.outcome == "thief_survival"
    assert result.audit_ok_police_side
    assert result.audit_ok_thief_side
    assert result.steps == result.survival_threshold
    assert result.game_uid  # both peers derived the same shared id
    assert result.police_state is GameState.GAME_OVER
    assert result.thief_state is GameState.GAME_OVER
    assert result.scores == (result.survival_cop_points, result.survival_thief_points)


def test_minigame_is_reproducible_for_fixed_seeds() -> None:
    a = run_local_minigame(CONFIG_DIR, police_seed=7, thief_seed=13)
    b = run_local_minigame(CONFIG_DIR, police_seed=7, thief_seed=13)
    assert a.police_moves == b.police_moves
    assert a.thief_moves == b.thief_moves


def test_fake_transport_rejects_unknown_tools() -> None:
    server = FakeMcpServer(tools={"negotiate": lambda payload: {"status": "ok"}})
    client = FakeMcpClient(server)
    assert client.call("negotiate", {})["status"] == "ok"
    try:
        client.call("submit_audit", {})
        raise AssertionError("unknown tool must raise")
    except KeyError:
        pass
