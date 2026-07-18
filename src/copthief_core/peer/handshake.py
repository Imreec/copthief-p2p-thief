"""Pre-game handshake (PLAN §4; M2 F2): the symmetric signed-terms exchange.

Split from the session (reference-mirroring the same split) so the session file stays
within the 150-line rule. Each peer sends `{terms, nonce, signature, group_id, role}` and
verifies the opponent signed value-equal terms; the shared `game_uid` derives with no
extra round-trip.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from copthief_core.domain.crypto import (
    canonical_hash,
    canonical_str,
    game_uid,
    make_nonce,
    terms_signature,
)
from copthief_core.domain.scent import locked_model_document
from copthief_core.domain.terms import terms_from_config

if TYPE_CHECKING:  # annotation-only: the session imports THIS module at runtime
    from copthief_core.peer.session import PeerSession


class NegotiationError(RuntimeError):
    """The pre-game gate refused: terms drift or a bad signature (kit §4)."""


def negotiate_payload(session: PeerSession) -> dict[str, Any]:
    """Our side of the gate: terms + fresh-nonce signature + identity (F8: the
    reference's exact message shape — identity is a dict, NOT signed, and the
    opponent reads our group id from identity.group_id)."""
    terms = terms_from_config(session.constitution)
    nonce = make_nonce()
    pheromones = session.constitution.pheromones
    scent_model = locked_model_document(
        center_intensity=pheromones.center_intensity,
        decay=pheromones.decay,
        grid_size=pheromones.grid_size,
        min_center_intensity=pheromones.min_center_intensity,
    )
    session.scent_model_hash = canonical_hash(scent_model)
    return {
        "terms": terms,
        "nonce": nonce,
        "signature": terms_signature(terms, nonce),
        # PRD_scent §4: the locked scent model rides the negotiate extras — the
        # reference reads only its four keys (verify_peer indexes them), so the
        # extra key is ignored by it and logged by us (hashes on the session).
        "scent_model": scent_model,
        # F8b: all seven keys the reference's declaration writer dereferences;
        # spec stays {} until shared/sysinfo lands (M6-3) — its fields are .get()-safe.
        "identity": {
            "group_id": session.private.group_id,
            "group_name": session.private.group_name,
            "members": list(session.private.members),
            "repos": dict(session.private.repos),
            "mcp_servers": dict(session.private.mcp_servers),
            "llm_model": session.private.llm_model,
            "spec": {},
        },
    }


def handle_negotiate(session: PeerSession, raw: dict[str, Any]) -> dict[str, Any]:
    """Verify value-equal terms + the opponent's signature; lock the game_uid."""
    ours = terms_from_config(session.constitution)
    theirs = raw.get("terms")
    if canonical_str(theirs) != canonical_str(ours):
        raise NegotiationError("terms mismatch: opponent terms do not value-equal ours")
    if terms_signature(ours, str(raw.get("nonce"))) != raw.get("signature"):
        raise NegotiationError("signature verification failed over our terms")
    identity = raw.get("identity") or {}
    # F8: the reference carries the group id inside `identity`; "unknown-group"
    # mirrors its own default so both sides degrade identically if it is absent.
    session.opponent_group = str(identity.get("group_id", raw.get("group_id", "unknown-group")))
    # PRD_scent §4: record the opponent's locked-model hash when they sent one (ours
    # arrives via negotiate_payload); the reference sends none — that is not a refusal.
    theirs_model = raw.get("scent_model")
    session.opponent_scent_model_hash = (
        canonical_hash(theirs_model) if theirs_model is not None else None
    )
    session.game_uid = game_uid(ours, session.private.group_id, session.opponent_group)
    return {"status": "ok", "game_uid": session.game_uid}
