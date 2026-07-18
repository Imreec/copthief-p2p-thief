"""Log schema v1.1 (PRD_gui_replay §3, workstream L): the observability event stream.

One local mini-game is the fixture: every inbound structure must be archived verbatim
(pre-validation), and the PLAN §7-promised belief/transition/decision events must ride
the same log. Closes the gap flagged in both M3 friendly evidence docs.
"""

import threading
from pathlib import Path
from typing import Any

import pytest

from copthief_core.domain.crypto import terms_signature
from copthief_core.domain.state_machine import GameState, GameStateMachine
from copthief_core.peer.match import run_local_minigame
from copthief_core.peer.p2p import run_peer_game
from copthief_core.peer.replay import replay_from_log
from copthief_core.peer.session import PeerSession, ProtocolViolationError
from copthief_core.peer.transport import queue_pair
from copthief_core.shared.config import load_all
from copthief_core.shared.jsonl_logger import read_events
from copthief_core.strategy.brains import make_brain

CONFIG_DIR = Path("config")
CONSTITUTION, PRIVATE, _LIMITS = load_all(CONFIG_DIR, counted=False)


@pytest.fixture(scope="module")
def game_events(tmp_path_factory: pytest.TempPathFactory) -> list[dict[str, Any]]:
    log_path = tmp_path_factory.mktemp("logs") / "game.jsonl"
    run_local_minigame(CONFIG_DIR, police_seed=11, thief_seed=22, log_path=log_path)
    return read_events(log_path)


def _of(events: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [e for e in events if e["event"] == kind]


def test_inbound_agreements_are_archived_verbatim(game_events: list[dict[str, Any]]) -> None:
    archived = _of(game_events, "agreement_received")
    assert {e["receiver"] for e in archived} == {"police", "thief"}
    for event in archived:
        raw = event["raw"]
        # Verbatim means verifiable: the archived object still passes the signature
        # check, exactly as the handshake saw it (kit terms-signature construction).
        assert terms_signature(raw["terms"], raw["nonce"]) == raw["signature"]
        assert "identity" in raw


def test_inbound_turns_are_archived_verbatim(game_events: list[dict[str, Any]]) -> None:
    turns = _of(game_events, "turn")
    archived = _of(game_events, "turn_received")
    assert len(archived) == len(turns)
    for turn in turns:
        matches = [
            e for e in archived if e["raw"] == turn["message"] and e["receiver"] != turn["sender"]
        ]
        assert len(matches) == 1, f"turn step {turn['message']['step']} not archived verbatim"


def test_opponent_audits_are_archived_verbatim(game_events: list[dict[str, Any]]) -> None:
    sent = {e["payload"]["sender"]: e["payload"] for e in _of(game_events, "audit")}
    archived = _of(game_events, "audit_received")
    assert {e["receiver"] for e in archived} == {"police", "thief"}
    for event in archived:
        opponent = "thief" if event["receiver"] == "police" else "police"
        assert event["raw"] == sent[opponent]


def test_transitions_are_logged_legal_and_terminal(game_events: list[dict[str, Any]]) -> None:
    for role in ("police", "thief"):
        chain = [e["payload"] for e in _of(game_events, "transition") if e["sender"] == role]
        assert chain, f"no transition events for {role}"
        # Replaying the chain through the real machine proves legality of every hop.
        machine = GameStateMachine(state=GameState(chain[0]["from"]))
        for hop in chain:
            assert machine.state is GameState(hop["from"])
            machine.advance(GameState(hop["to"]))
        assert machine.state is GameState.GAME_OVER


def test_belief_snapshot_rides_every_inbound_turn(game_events: list[dict[str, Any]]) -> None:
    for role in ("police", "thief"):
        inbound = [e for e in _of(game_events, "turn_received") if e["receiver"] == role]
        beliefs = [e["payload"] for e in _of(game_events, "belief") if e["sender"] == role]
        assert beliefs, f"no belief snapshots for {role}"
        assert len(beliefs) == len(inbound)
        assert [b["step"] for b in beliefs] == list(range(1, len(beliefs) + 1))
        for snapshot in beliefs:
            assert sum(snapshot["grid"].values()) == pytest.approx(1.0)
            assert snapshot["argmax"] in snapshot["grid"]


def test_decisions_carry_provenance_matching_the_audit(game_events: list[dict[str, Any]]) -> None:
    sealed = {
        (e["payload"]["sender"], r["payload"]["step"]): r["payload"]
        for e in _of(game_events, "audit")
        for r in e["payload"]["records"]
    }
    for role in ("police", "thief"):
        decisions = [e["payload"] for e in _of(game_events, "decision") if e["sender"] == role]
        assert len(decisions) == len([e for e in _of(game_events, "turn") if e["sender"] == role])
        # Role-blind (PR #29 rule): the expected brain is whatever the local repo's
        # game.toml [strategy] resolves to through the factory.
        expected_class = PRIVATE.police_class if role == "police" else PRIVATE.thief_class
        expected_brain = type(make_brain(expected_class, seed=0)).__name__
        for decision in decisions:
            record = sealed[(role, decision["step"])]
            assert decision["brain"] == expected_brain  # game.toml [strategy] pin
            assert decision["move"] == record["move"]
            assert decision["intent"] == record["intent"]


def test_rejected_inbound_turn_is_still_archived() -> None:
    # Dispute evidence: a protocol-violating message is archived BEFORE validation.
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=11)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=22)
    police_t, thief_t = queue_pair(wait_timeout=PRIVATE.connect_timeout_seconds)
    garbage = {"nonsense": True, "step": "not-an-int"}
    captured: list[dict[str, Any]] = []

    def feed() -> None:
        thief_t.exchange_agreement(thief.negotiate_payload())
        thief_t.send_turn(garbage)

    feeder = threading.Thread(target=feed)
    feeder.start()
    with pytest.raises(ProtocolViolationError):
        run_peer_game(
            police,
            police_t,
            turn_timeout=PRIVATE.turn_timeout_seconds,
            poll_interval=PRIVATE.poll_interval_seconds,
            log=captured.append,
        )
    feeder.join(timeout=PRIVATE.connect_timeout_seconds)
    archived = [e for e in captured if e["event"] == "turn_received"]
    assert [e["raw"] for e in archived] == [garbage]
    losses = [e for e in captured if e["event"] == "transition"]
    assert losses[-1]["payload"]["to"] == "technical_loss"
    assert losses[-1]["payload"]["trigger"] != ""  # the collapse reason travels


def test_pre_schema_evidence_log_still_replays_verified() -> None:
    # Backward-compat pin (PRD_gui_replay §3): the committed M3 live evidence logs
    # verify unchanged — new event kinds must never break old-log replay. Globbed,
    # not named: this test is core-mirrored and each role repo commits its own M3
    # friendly log (cop: m3-scent-friendly-g1; thief: m3-full-pairing-g1).
    logs = sorted(Path("docs/evidence").glob("m3-*.jsonl"))
    assert logs, "no pre-schema M3 evidence log committed in this repo"
    for log in logs:
        summary = replay_from_log(log)
        assert summary.verified, f"{log.name}: {summary.problems}"
        assert summary.problems == []
