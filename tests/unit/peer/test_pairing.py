"""The handshake must say WHICH game and WHICH side (M7-10, mutual with Alon/Renat).

Until now `negotiate` carried `{identity, nonce, scent_model_sha256, signature, terms}` —
nothing in it names the sub-game or the role, so two peers can shake hands while
completely disagreeing about what they are doing. Both failures have been seen:

- **Two peers that had BOTH taken thief** completed a handshake and then deadlocked after
  one turn, each waiting for a police move that was never coming (observed in the M7-4c
  live series run).
- **One game wearing two indices** — the 2026-07-24 rehearsal's "phantom sub-game 6" was
  his s6 and our s2, and neither side could tell, because identical terms produce
  identical `game_uid`s and the handshake had nothing in it that could disagree.

The refusal truth table follows the one the kit already uses for locked-model
declarations (SPEC §7): a declared mismatch refuses, **omission never refuses**. The
reference peer declares neither field, and a lock that fail-fasts on silence forfeits
that game to itself.
"""

from __future__ import annotations

import pytest

from copthief_core.peer.pairing import ROLE_KEY, SUB_GAME_KEY, pairing_problem


def _problem(declared: dict[str, object], *, index: int = 3, role: str = "police") -> str | None:
    return pairing_problem(sub_game_number=index, role=role, declared=declared)


def test_a_matching_pairing_is_accepted() -> None:
    assert _problem({SUB_GAME_KEY: 3, ROLE_KEY: "thief"}) is None


def test_a_different_sub_game_index_refuses() -> None:
    """The phantom-s6 shape: same terms, same game_uid, two different games."""
    problem = _problem({SUB_GAME_KEY: 6, ROLE_KEY: "thief"})
    assert problem is not None
    assert "sub-game" in problem
    assert "6" in problem  # both indices named, so the log is usable
    assert "3" in problem


def test_a_peer_claiming_our_own_role_refuses() -> None:
    """Roles must be complementary, not equal — two thieves deadlock politely."""
    problem = _problem({SUB_GAME_KEY: 3, ROLE_KEY: "police"}, role="police")
    assert problem is not None
    assert "role" in problem


def test_a_peer_that_declares_nothing_is_still_playable() -> None:
    """Omission never refuses: the reference declares neither field, and neither did we
    until today. A guard that fail-fasts on silence forfeits the game to itself."""
    assert _problem({}) is None
    assert _problem({"terms": {}, "nonce": "x"}) is None


def test_each_field_is_judged_on_its_own() -> None:
    """A peer that has built one half of this must not be refused for the other."""
    assert _problem({SUB_GAME_KEY: 3}) is None
    assert _problem({ROLE_KEY: "thief"}) is None
    assert _problem({SUB_GAME_KEY: 4}) is not None
    assert _problem({ROLE_KEY: "police"}, role="police") is not None


@pytest.mark.parametrize("declared", ["3", 3.0, None, [], {}])
def test_an_unusable_index_is_treated_as_undeclared_not_as_a_mismatch(
    declared: object,
) -> None:
    """A value we cannot compare is silence, not disagreement. Refusing on a peer's
    type choice would turn a cosmetic wire difference into a forfeited game — and the
    rehearsal already lost a window to `payload` vs `message`."""
    assert _problem({SUB_GAME_KEY: declared}) is None


def test_the_role_comparison_ignores_case_and_padding() -> None:
    """Same reasoning: a spelling difference must not decide a game."""
    assert _problem({ROLE_KEY: " Police "}, role="police") is not None
    assert _problem({ROLE_KEY: "THIEF"}, role="police") is None


def test_a_stranger_is_refused_when_we_know_who_we_are_playing() -> None:
    """M7-45, from uoh-sqak's 2026-08-07 fix and our own worse version of the hole.

    We checked the declared index and role and never checked WHO answered. A stranger
    declaring a matching index and the complementary role was therefore ACCEPTED — we
    would have played them and sealed the game into the series under the real opponent's
    group id. Their bug burned windows; ours would have produced a false record.
    """
    stranger = {SUB_GAME_KEY: 3, ROLE_KEY: "thief", "identity": {"group_id": "najamjad"}}
    problem = pairing_problem(
        sub_game_number=3, role="police", declared=stranger, expected_group="uoh-sqak"
    )
    assert problem is not None
    assert "najamjad" in problem  # names who actually answered
    assert "uoh-sqak" in problem  # and who we were expecting


def test_the_declared_opponent_is_accepted() -> None:
    theirs = {SUB_GAME_KEY: 3, ROLE_KEY: "thief", "identity": {"group_id": "uoh-sqak"}}
    assert (
        pairing_problem(
            sub_game_number=3, role="police", declared=theirs, expected_group="uoh-sqak"
        )
        is None
    )


def test_an_unknown_opponent_accepts_whoever_answers() -> None:
    """Empty stays permissive: self-tests, the reference oracle and unplanned peers all
    negotiate without anyone having named an opponent in advance."""
    anyone = {SUB_GAME_KEY: 3, ROLE_KEY: "thief", "identity": {"group_id": "whoever"}}
    assert (
        pairing_problem(sub_game_number=3, role="police", declared=anyone, expected_group=None)
        is None
    )


def test_an_undeclared_group_never_refuses() -> None:
    """Omission never refuses — the same rule the index and role checks use, and the
    reference declares no group id at all."""
    silent = {SUB_GAME_KEY: 3, ROLE_KEY: "thief"}
    assert (
        pairing_problem(
            sub_game_number=3, role="police", declared=silent, expected_group="uoh-sqak"
        )
        is None
    )
