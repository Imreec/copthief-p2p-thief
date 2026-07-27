"""M7-22: declare the derived game_uid at negotiate; refuse a comparable mismatch.

The uid never crosses the wire — each side derives it independently — so when the
opponent team derived theirs from the WRONG INPUT (their whole game.json instead of
the flat negotiated terms), the divergence stayed silent for an entire six-sub-game
series and surfaced only at the next morning's report diff. Declaring the derivation
in the greeting turns that morning-after into a T+9s refusal, in exactly the M7-10
pattern: outside `terms` (the signature is untouched), refusal only on a COMPARABLE
mismatch, omission never refuses (the reference declares nothing), an uncomparable
value is silence.

The declarer needs to know its opponent a priori (the uid is pair-dependent), which a
series run does (`--opponent-group`); a one-off peer without it simply omits the key.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from copthief_core.domain.crypto import game_uid
from copthief_core.domain.terms import terms_from_config
from copthief_core.peer.handshake import NegotiationError
from copthief_core.peer.sealing import live_spec_record
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


def _session(role: str, *, expects: str | None = None) -> PeerSession:
    return PeerSession(
        CONSTITUTION,
        PRIVATE,
        role=role,
        seed=1,
        spec_record=live_spec_record(PRIVATE, CONSTITUTION, sub_game_number=4),
        expected_opponent_group=expects,
    )


def _their_payload(session: PeerSession, **extra: object) -> dict:
    other = "thief" if session.role == "police" else "police"
    payload = _session(other, expects=PRIVATE.group_id).negotiate_payload()
    payload.update(extra)
    return payload


def test_a_peer_that_knows_its_opponent_declares_the_derived_uid() -> None:
    session = _session("police", expects="anrbj666")
    payload = session.negotiate_payload()
    expected = game_uid(terms_from_config(CONSTITUTION), PRIVATE.group_id, "anrbj666")
    assert payload["game_uid"] == expected
    assert "game_uid" not in payload["terms"]  # outside the signed constitution


def test_a_peer_without_a_known_opponent_omits_the_key() -> None:
    payload = _session("police").negotiate_payload()
    assert "game_uid" not in payload


def test_matching_declarations_negotiate_cleanly() -> None:
    session = _session("police", expects=PRIVATE.group_id)
    result = session.handle_negotiate(_their_payload(session))
    assert result["status"] == "ok"


def test_a_comparable_uid_mismatch_refuses_naming_the_derivation() -> None:
    """The opponent's 2026-07-25 bug, caught at the handshake: a deterministic uid
    hashed over the wrong input is stable, self-consistent, and WRONG."""
    session = _session("police", expects=PRIVATE.group_id)
    wrong = "2f0c25a9-5008-03c7-2d60-645dd51be11a"
    with pytest.raises(NegotiationError, match="game_uid mismatch.*terms input"):
        session.handle_negotiate(_their_payload(session, game_uid=wrong))


def test_omission_never_refuses() -> None:
    """The reference declares nothing; a lock that fail-fasts on silence forfeits
    the game to itself (the SPEC §7 truth table, applied unchanged)."""
    session = _session("police", expects=PRIVATE.group_id)
    payload = _their_payload(session)
    payload.pop("game_uid", None)
    assert session.handle_negotiate(payload)["status"] == "ok"


def test_an_uncomparable_value_is_silence_not_disagreement() -> None:
    session = _session("police", expects=PRIVATE.group_id)
    assert session.handle_negotiate(_their_payload(session, game_uid=1234))["status"] == "ok"
