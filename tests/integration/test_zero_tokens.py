"""M6-8: the 0-token claim is cryptographically auditable, permanently, in CI.

COST.md's headline claim rests on two independent proofs (PRD_reporting §7): the
JSONL event log AND the sealed per-step token counts (M6-3). This pin exercises
the second on a real audited game: every sealed game record carries
tokens_step == tokens_total == 0 under the template verbal layer — and because
those fields sit INSIDE the commit-reveal payload, replay re-verification makes
the claim tamper-evident, not just logged.
"""

from __future__ import annotations

from pathlib import Path

from copthief_core.peer.match import run_local_minigame
from copthief_core.peer.replay import VERDICT_OK, replay_from_log, verdict_for
from copthief_core.shared.jsonl_logger import read_events

CONFIG_DIR = Path("config")


def test_every_sealed_record_charges_zero_tokens_and_survives_replay(tmp_path: Path) -> None:
    log_path = tmp_path / "game.jsonl"
    run_local_minigame(CONFIG_DIR, police_seed=11, thief_seed=22, log_path=log_path)
    events = read_events(log_path)
    audits = [e for e in events if e["event"] == "audit"]
    assert len(audits) == 2  # both sides sealed and revealed
    game_records = 0
    for audit in audits:
        for record in audit["payload"]["records"]:
            payload = record["payload"]
            if payload.get("step", 0) >= 1:
                game_records += 1
                assert payload["tokens_step"] == 0
                assert payload["tokens_total"] == 0
    assert game_records > 0
    # The counts are sealed, so the claim is tamper-evident: the log re-verifies.
    assert verdict_for(replay_from_log(log_path)) == VERDICT_OK
