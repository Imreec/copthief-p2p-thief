"""The info_mode lock declared at negotiate (M7-25; kit SPEC §7; ADR-0010 §84).

Round-16 outcome with the opponent team: `info_mode: belief` for the counted series —
the transmitted field reaches decisions only through a probabilistic belief layer, no
deterministic inversion pin. The posture was an honor term; declaring its registration
hash at the handshake makes it a both-declared lock: two `belief` declarations on the
record, each backed by the validator firewall test both teams ship. Same truth table
as every negotiate extra (M3-8/M7-10/M7-22): both-declare-and-differ refuses, omission
never refuses, the doc never crosses the wire.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from copthief_core.peer.session import NegotiationError, PeerSession
from copthief_core.shared.config import load_all
from copthief_core.shared.locked_models import INFO_MODE, LockedModelRegistry

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
DECLARED = LockedModelRegistry.declared_key(INFO_MODE)


def _pair() -> tuple[PeerSession, PeerSession]:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    thief.handle_negotiate(police.negotiate_payload())
    police.handle_negotiate(thief.negotiate_payload())
    return police, thief


def test_negotiate_declares_the_info_mode_hash_and_never_the_document() -> None:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    payload = police.negotiate_payload()
    assert payload[DECLARED] == PRIVATE.locked_models.hash(INFO_MODE, PRIVATE.info_mode)
    assert "info_mode" not in payload  # only the hash crosses (kit SPEC §7)


def test_config_defaults_to_belief_and_selects_the_declared_mode() -> None:
    assert PRIVATE.info_mode == "belief"  # our shipped posture — the firewall's twin
    exact = PeerSession(CONSTITUTION, replace(PRIVATE, info_mode="exact"), role="police", seed=1)
    assert exact.negotiate_payload()[DECLARED] == PRIVATE.locked_models.hash(INFO_MODE, "exact")


def test_handshake_records_both_info_mode_hashes() -> None:
    police, thief = _pair()
    ours = PRIVATE.locked_models.hash(INFO_MODE, PRIVATE.info_mode)
    assert police.info_mode_hash == ours
    assert police.opponent_info_mode_hash == ours  # same shipped config both sides
    assert thief.opponent_info_mode_hash == police.info_mode_hash


def test_omission_never_refuses_reference_compat() -> None:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    payload = thief.negotiate_payload()
    del payload[DECLARED]  # the unmodified reference declares nothing
    police.handle_negotiate(payload)
    assert police.opponent_info_mode_hash is None
    assert police.game_uid is not None  # the handshake still completes


def test_both_declare_and_differ_refuses_the_game() -> None:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    payload = thief.negotiate_payload()
    payload[DECLARED] = PRIVATE.locked_models.hash(INFO_MODE, "exact")
    with pytest.raises(NegotiationError, match="locked info mode mismatch"):
        police.handle_negotiate(payload)
