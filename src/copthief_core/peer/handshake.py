"""Pre-game handshake (PLAN §4; M2 F2): the symmetric signed-terms exchange.

Split from the session (reference-mirroring the same split) so the session file stays
within the 150-line rule. Each peer sends `{terms, nonce, signature, group_id, role}` and
verifies the opponent signed value-equal terms; the shared `game_uid` derives with no
extra round-trip.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from copthief_core.domain.crypto import (
    canonical_str,
    game_uid,
    make_nonce,
    terms_signature,
)
from copthief_core.domain.terms import terms_from_config

if TYPE_CHECKING:  # annotation-only: the session imports THIS module at runtime
    from copthief_core.peer.session import PeerSession


class NegotiationError(RuntimeError):
    """The pre-game gate refused: terms drift or a bad signature (kit §4)."""


def negotiate_payload(session: PeerSession) -> dict[str, Any]:
    """Our side of the gate: terms + fresh-nonce signature + identity."""
    terms = terms_from_config(session.constitution)
    nonce = make_nonce()
    return {
        "group_id": session.private.group_id,
        "role": session.role,
        "terms": terms,
        "nonce": nonce,
        "signature": terms_signature(terms, nonce),
    }


def handle_negotiate(session: PeerSession, raw: dict[str, Any]) -> dict[str, Any]:
    """Verify value-equal terms + the opponent's signature; lock the game_uid."""
    ours = terms_from_config(session.constitution)
    theirs = raw.get("terms")
    if canonical_str(theirs) != canonical_str(ours):
        raise NegotiationError("terms mismatch: opponent terms do not value-equal ours")
    if terms_signature(ours, str(raw.get("nonce"))) != raw.get("signature"):
        raise NegotiationError("signature verification failed over our terms")
    session.opponent_group = str(raw.get("group_id"))
    session.game_uid = game_uid(ours, session.private.group_id, session.opponent_group)
    return {"status": "ok", "game_uid": session.game_uid}
