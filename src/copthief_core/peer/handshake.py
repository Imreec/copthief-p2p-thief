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
from copthief_core.peer.pairing import pairing_declaration, pairing_problem
from copthief_core.shared.locked_models import (
    SCENT_MODEL,
    LockedModelRegistry,
    lock_decision,
)

if TYPE_CHECKING:  # annotation-only: the session imports THIS module at runtime
    from copthief_core.peer.session import PeerSession


class NegotiationError(RuntimeError):
    """The pre-game gate refused: terms drift or a bad signature (kit §4)."""


class PairingRefusalError(NegotiationError):
    """The agreement belongs to a DIFFERENT game: wrong sub-game index or our own
    role (M7-10). Distinct from its parent because the caller's response differs —
    against a role-split opponent their next window's peer pushes early at our one
    port, and its agreement carries the identical signed terms with a valid
    signature; it fails only here. That is a bystander to refuse and outwait, not
    a reason to die (M7-11b). Terms drift and bad signatures stay fatal."""


def negotiate_payload(session: PeerSession) -> dict[str, Any]:
    """Our side of the gate: terms + fresh-nonce signature + identity (F8: the
    reference's exact message shape — identity is a dict, NOT signed, and the
    opponent reads our group id from identity.group_id)."""
    terms = terms_from_config(session.constitution)
    nonce = make_nonce()
    registry: LockedModelRegistry = session.private.locked_models
    session.scent_model_hash = registry.hash(SCENT_MODEL, session.private.scent_model)
    return {
        "terms": terms,
        "nonce": nonce,
        "signature": terms_signature(terms, nonce),
        # M7-10: which game, and which side. Outside `terms` on purpose — that is the
        # byte-identical signed constitution, so a per-sub-game value cannot live there.
        **pairing_declaration(sub_game_number=declared_sub_game(session), role=session.role),
        # M3-8 (kit SPEC §7): the DOC never crosses the wire — only its hash, under
        # `<family>_sha256`. The reference reads only its four keys (verify_peer
        # indexes them), so the extra key is ignored by it and compared by us.
        registry.declared_key(SCENT_MODEL): session.scent_model_hash,
        # F8b: all seven keys the reference's declaration writer dereferences; the
        # spec comes from OUR sealed step-0 record (M6-3) so the identity we hand the
        # opponent and the declaration we seal can never disagree.
        "identity": {
            "group_id": session.private.group_id,
            "group_name": session.private.group_name,
            "members": list(session.private.members),
            "repos": dict(session.private.repos),
            "mcp_servers": dict(session.private.mcp_servers),
            "llm_model": session.private.llm_model,
            "spec": (
                session.spec_record.payload["spec"] if session.spec_record is not None else {}
            ),
        },
    }


def declared_sub_game(session: PeerSession) -> int:
    """The sub-game index we declare (Input: the session; Output: the SEALED index when
    a step-0 record exists, the configured one otherwise).

    Read from the sealed record rather than the config so the handshake and the step-0
    commit cannot disagree: the whole point is that one game cannot carry two indices.
    """
    if session.spec_record is not None:
        return int(session.spec_record.payload["sub_game_number"])
    return session.private.sub_game_number


def handle_negotiate(session: PeerSession, raw: dict[str, Any]) -> dict[str, Any]:
    """Verify value-equal terms + the opponent's signature; lock the game_uid."""
    ours = terms_from_config(session.constitution)
    theirs = raw.get("terms")
    # Absence is a different diagnosis from disagreement (2026-07-25 friendly, T3):
    # a greeting with NO terms is the bookletter shape (config_sha256 substitution)
    # arriving under a reference wire — a wire-shape fault on the sender's side, not
    # a constitution drift. Naming it saves the two hours it cost to see the first time.
    if theirs is None:
        raise NegotiationError(
            "opponent agreement carries no terms at all — a bookletter-shaped "
            "greeting under a reference wire (kit CORE: flat terms + nonce + signature)"
        )
    if canonical_str(theirs) != canonical_str(ours):
        raise NegotiationError("terms mismatch: opponent terms do not value-equal ours")
    if terms_signature(ours, str(raw.get("nonce"))) != raw.get("signature"):
        raise NegotiationError("signature verification failed over our terms")
    # M7-10: BEFORE the game_uid is locked. Identical terms give identical game_uids, so
    # by the time an artifact exists a mispairing is already invisible — the handshake is
    # the only place it can still be seen.
    mispairing = pairing_problem(
        sub_game_number=declared_sub_game(session), role=session.role, declared=raw
    )
    if mispairing is not None:
        raise PairingRefusalError(mispairing)
    identity = raw.get("identity") or {}
    # F8: the reference carries the group id inside `identity`; "unknown-group"
    # mirrors its own default so both sides degrade identically if it is absent.
    session.opponent_group = str(identity.get("group_id", raw.get("group_id", "unknown-group")))
    # M3-8 (kit SPEC §7 refusal rule): record the opponent's declared model hash, then
    # refuse ONLY when both sides declared and the hashes differ. Omission — theirs or
    # ours — is never refusal: the unmodified reference peer declares nothing, and a
    # lock that fail-fasts on silence forfeits that game to itself (ADR-0004 v2).
    declared = raw.get(LockedModelRegistry.declared_key(SCENT_MODEL))
    session.opponent_scent_model_hash = str(declared) if declared is not None else None
    ours_model = session.scent_model_hash or session.private.locked_models.hash(
        SCENT_MODEL, session.private.scent_model
    )
    if lock_decision(ours_model, session.opponent_scent_model_hash) == "refuse":
        raise NegotiationError(
            "locked scent model mismatch: we declared "
            f"{ours_model}, opponent declared {session.opponent_scent_model_hash}"
        )
    session.game_uid = game_uid(ours, session.private.group_id, session.opponent_group)
    return {"status": "ok", "game_uid": session.game_uid}
