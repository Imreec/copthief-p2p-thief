"""The pairing declaration on the real handshake (M7-10).

`peer/pairing` is the pure judgement; this pins that the session actually SENDS the two
facts and actually REFUSES on a contradiction — the half that is ours to build, and which
sits inert until the opponent sends the fields too (omission never refuses).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from copthief_core.peer.handshake import NegotiationError
from copthief_core.peer.pairing import ROLE_KEY, SUB_GAME_KEY
from copthief_core.peer.sealing import live_spec_record
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


def _session(role: str, sub_game_number: int | None) -> PeerSession:
    return PeerSession(
        CONSTITUTION,
        PRIVATE,
        role=role,
        seed=1,
        spec_record=live_spec_record(PRIVATE, CONSTITUTION, sub_game_number=sub_game_number),
    )


def _their_payload(session: PeerSession, **extra: object) -> dict:
    """The opponent's agreement, built by a mirror session so the terms really match."""
    other = "thief" if session.role == "police" else "police"
    payload = _session(other, 4).negotiate_payload()
    payload.update(extra)
    return payload


def test_we_declare_the_sealed_index_and_our_role() -> None:
    session = _session("police", 4)
    payload = session.negotiate_payload()

    assert payload[ROLE_KEY] == "police"
    # The SEALED index, not the config default — the handshake and the step-0 commit
    # must be incapable of disagreeing about which sub-game this is.
    assert payload[SUB_GAME_KEY] == session.spec_record.payload["sub_game_number"] == 4


def test_a_matching_opponent_still_negotiates_cleanly() -> None:
    session = _session("police", 4)
    result = session.handle_negotiate(_their_payload(session))
    assert result["status"] == "ok"
    assert result["game_uid"]


def test_an_opponent_on_a_different_sub_game_is_refused() -> None:
    """The phantom-s6 shape, caught at the handshake instead of in the artifacts."""
    session = _session("police", 4)
    with pytest.raises(NegotiationError, match="sub-game mismatch"):
        session.handle_negotiate(_their_payload(session, **{SUB_GAME_KEY: 6}))


def test_an_opponent_claiming_our_role_is_refused() -> None:
    session = _session("police", 4)
    with pytest.raises(NegotiationError, match="role collision"):
        session.handle_negotiate(_their_payload(session, **{ROLE_KEY: "police"}))


def test_a_peer_that_declares_neither_field_is_still_played() -> None:
    """The reference declares neither, and so did we until today: our refusal is inert
    until the opponent sends the fields, which is why this fix is being built mutually."""
    session = _session("police", 4)
    payload = _their_payload(session)
    payload.pop(SUB_GAME_KEY)
    payload.pop(ROLE_KEY)
    assert session.handle_negotiate(payload)["status"] == "ok"


def test_the_declaration_does_not_disturb_the_signed_terms() -> None:
    """Constraint #13: the two keys ride OUTSIDE `terms`, which is the byte-identical
    signed constitution — a per-sub-game value could never live there."""
    payload = _session("thief", 2).negotiate_payload()
    assert SUB_GAME_KEY not in payload["terms"]
    assert ROLE_KEY not in payload["terms"]


def test_negotiate_payload_carries_the_reference_identity_shape() -> None:
    # M2 Stage A finding F8 (oracle sha 960499fd): the reference reads the opponent's
    # group id from message["identity"]["group_id"] — without it we were filed as
    # "unknown-group" and the two sides derived DIFFERENT game_uids (observed live).
    payload = _session("police", 4).negotiate_payload()
    # M3-2 adds the locked scent-model extra (PRD_scent §4) — safe against the
    # reference because its verify_peer indexes only its own four keys (source-pinned).
    # M3-8 (kit SPEC §7): the locked model rides as a HASH under `scent_model_sha256`;
    # the pre-M3-8 full-document `scent_model` key is gone. The reference ignores both.
    # M7-10 adds `sub_game_number` + `role` — the two facts the handshake never carried,
    # so two peers could agree on everything signed and still be playing different games
    # (one game under two indices; or both having taken thief). Same safety argument as
    # the M3-8 extra: the reference indexes only its own four keys, so it ignores these,
    # and our own refusal treats an absent field as silence rather than disagreement.
    assert set(payload) == {
        "terms",
        "nonce",
        "signature",
        "identity",
        "scent_model_sha256",
        "sub_game_number",
        "role",
    }
    # F8b (observed live): the reference's declaration writer group_block() KeyErrors
    # unless the identity carries all seven reference keys.
    assert set(payload["identity"]) == {
        "group_id",
        "group_name",
        "members",
        "repos",
        "mcp_servers",
        "llm_model",
        "spec",
    }
    assert payload["identity"]["group_id"] == PRIVATE.group_id
    assert payload["identity"]["group_name"] == PRIVATE.group_name
    assert payload["identity"]["members"] == list(PRIVATE.members)
    assert isinstance(payload["identity"]["spec"], dict)
