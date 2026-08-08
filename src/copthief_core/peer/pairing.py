"""Which game, and which side (M7-10): the two facts the handshake never carried.

`negotiate` declares terms, a nonce, a signature, an identity and the locked model
hashes — and nothing that says *this is sub-game 4* or *I am the police*. Two peers can
therefore agree on everything that is signed and still be playing different games:

- both having taken **thief**, they shake hands and deadlock after one turn, each waiting
  for a move the other will never make (seen in the M7-4c live series run);
- or they play the same game under **two different indices** — the 2026-07-24 rehearsal's
  "phantom sub-game 6" was his s6 and our s2, undetectable from either side because
  identical terms give identical `game_uid`s.

Both are settled here, before a single state change, by declaring the two facts and
refusing a peer that contradicts them.

**Omission never refuses** — the same rule the kit's locked-model declarations use (SPEC
§7). The reference peer declares neither field, and we ourselves declared neither until
today; a guard that fail-fasts on silence forfeits that game to itself. A value we cannot
compare is treated as silence too: refusing over a peer's type or spelling choice would
turn a cosmetic wire difference into a lost game, and the rehearsal already spent a window
on `payload` versus `message`.
"""

from __future__ import annotations

from typing import Any

__all__ = ["ROLE_KEY", "SUB_GAME_KEY", "pairing_declaration", "pairing_problem"]

SUB_GAME_KEY = "sub_game_number"
ROLE_KEY = "role"


def pairing_declaration(*, sub_game_number: int, role: str) -> dict[str, Any]:
    """What we add to `negotiate` (Input: the SEALED sub-game index and our wire role;
    Output: the two declared keys).

    The index is the one sealed into the step-0 commit, never a config default read a
    second time: the handshake and the artifact must be incapable of disagreeing.
    """
    return {SUB_GAME_KEY: sub_game_number, ROLE_KEY: role}


def _wrong_group(declared: dict[str, Any], expected_group: str | None) -> str | None:
    """The refusal for an agreement from someone we are not playing, or None.

    Omission never refuses — the same rule the index and role checks use, and the
    reference declares no group id at all. Only a peer that NAMES a different group is
    turned away; the caller keeps listening inside the same budget, so a stranger costs
    nothing rather than costing a window.
    """
    if not expected_group:
        return None
    identity = declared.get("identity")
    theirs = identity.get("group_id") if isinstance(identity, dict) else declared.get("group_id")
    if not isinstance(theirs, str) or not theirs.strip():
        return None
    if theirs.strip().casefold() == expected_group.strip().casefold():
        return None
    return (
        f"wrong opponent: we are playing {expected_group!r}, this agreement is from "
        f"{theirs!r} — a stranger's game would be sealed under the wrong group id"
    )


def pairing_problem(
    *,
    sub_game_number: int,
    role: str,
    declared: dict[str, Any],
    expected_group: str | None = None,
) -> str | None:
    """Judge the opponent's declaration (Input: our index and role, their whole negotiate
    payload, and who we expect to be playing; Output: the refusal reason, or None).

    M7-45: WHO answered is checked, not just what they claim to be playing. Our endpoint
    is public and unauthenticated — anyone can call `negotiate` — and a stranger
    declaring a matching index and the complementary role passed every check we had. We
    would have played them and sealed the game into the series under the REAL opponent's
    group id: an artifact naming a team that never played it. uoh-sqak hit the cheaper
    half of this live (twelve stranger agreements consumed twelve of their windows,
    2026-08-07); ours would have produced a false record instead of a lost series.

    `expected_group` empty accepts whoever answers — self-tests, the reference oracle and
    unplanned peers all negotiate without an opponent named in advance.
    """
    stranger = _wrong_group(declared, expected_group)
    if stranger is not None:
        return stranger
    theirs = declared.get(SUB_GAME_KEY)
    # bool is an int in Python; a True here is a wire accident, not a sub-game.
    if isinstance(theirs, int) and not isinstance(theirs, bool) and theirs != sub_game_number:
        return (
            f"sub-game mismatch: we are playing sub-game {sub_game_number}, "
            f"the opponent declared {theirs} — one game cannot carry two indices"
        )
    their_role = declared.get(ROLE_KEY)
    if isinstance(their_role, str) and their_role.strip().casefold() == role.casefold():
        return (
            f"role collision: both peers declared {role!r} — the two sides of a game "
            "are complementary, and two of the same side can only deadlock"
        )
    return None
