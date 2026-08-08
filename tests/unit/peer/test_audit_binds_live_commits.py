"""A disclosed record must match the commitment that arrived LIVE (M7-56).

Commit-reveal only binds if the commitment is fixed BEFORE the reveal. We re-hashed each
disclosed record against the commit carried *inside that same record*, which a rewritten
record also satisfies — it is self-consistent because the rewriter wrote both halves. We
hold every live commit in `session.inbound` and never compared them.

So a peer could lose a sub-game, rewrite its moves into a version it won, seal fresh
commits, and our audit returned Verified OK. Nobody has done it; the point is that our
audit proved "their story is self-consistent" while we reported it as "their story is
what they committed to".

Raised independently by gal-roy1 (kit #48, their first finding) and implied by best2934's
`forged` verdict, which already does this check — so on 2026-08-08 their auditor was
strictly stronger than ours in the one direction that settles a counted game.

Records that never crossed the wire (step-0 `system_spec`, `control`) have no live
counterpart and are checked only against their own seal, as before.
"""

from __future__ import annotations

from dataclasses import replace as _replace
from pathlib import Path

from copthief_core.domain.crypto import commit as seal
from copthief_core.peer.audit_flow import verify_audit
from copthief_core.shared.config import load_all
from copthief_core.wire.audit import AuditPayload

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)
PRIVATE = _replace(_SHIPPED, police_class="random", thief_class="random")

NONCE = "a" * 32


def _record(step: int, move: str, *, nonce: str = NONCE) -> dict[str, object]:
    payload = {"step": step, "move": move, "role": "thief", "sub_game": 1}
    return {"payload": payload, "nonce": nonce, "commit": seal(payload, nonce)}


def _audit(records: list[dict[str, object]]) -> AuditPayload:
    return AuditPayload.from_wire(
        {"sender": "thief", "records": records, "result_claim": "survival"}
    )


def test_an_honest_disclosure_still_verifies() -> None:
    """The live commits are exactly the ones disclosed — nothing changes."""
    records = [_record(1, "N"), _record(2, "E")]
    live = {1: records[0]["commit"], 2: records[1]["commit"]}
    assert verify_audit(_audit(records), live_commits=live) == []


def test_a_rewritten_move_is_caught_even_though_it_reseals_cleanly() -> None:
    """THE POINT. They played N at step 1 and disclose S, re-sealed so the record is
    internally perfect. Only the commitment we were handed at the time refutes it."""
    played = _record(1, "N")
    rewritten = _record(1, "S")
    assert rewritten["commit"] != played["commit"]
    # self-consistent: the old check passes it
    assert verify_audit(_audit([rewritten])) == []
    # bound to what actually arrived: refused
    problems = verify_audit(_audit([rewritten]), live_commits={1: played["commit"]})
    assert problems
    assert "step 1" in problems[0]


def test_a_step_we_never_received_is_not_judged_against_a_commit_we_lack() -> None:
    """Absence is not evidence: a record whose step never reached us live is checked
    against its own seal only, exactly as before. Otherwise the first dropped turn in a
    flaky tunnel becomes an accusation of forgery."""
    records = [_record(1, "N"), _record(2, "E")]
    live = {1: records[0]["commit"]}  # step 2 never arrived
    assert verify_audit(_audit(records), live_commits=live) == []


def test_omitting_the_live_commits_keeps_the_historical_behaviour() -> None:
    """`live_commits=None` is the pre-M7-56 check — the referee harness, the replay
    tooling and every offline caller have no wire history to bind against."""
    assert verify_audit(_audit([_record(1, "N")])) == []


def test_a_non_game_record_is_not_bound_to_a_live_commit() -> None:
    """A step-0 declaration never crosses the wire, so there is nothing to bind it to."""
    spec = {"payload": {"step": 0, "type": "system_spec"}, "nonce": NONCE}
    spec["commit"] = seal(spec["payload"], NONCE)
    records = [spec, _record(1, "N")]
    live = {1: records[1]["commit"]}
    assert verify_audit(_audit(records), live_commits=live) == []
