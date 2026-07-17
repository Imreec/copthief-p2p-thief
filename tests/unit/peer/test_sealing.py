"""Sealing (PRD_crypto §4): the self-consistent record, kit-pinned state string."""

from copthief_core.domain.crypto import verify
from copthief_core.peer.sealing import seal_turn, state_string


def test_state_string_matches_the_kit_vector_form_no_barriers() -> None:
    # Byte-exact vs tests/conformance/vectors/commit_reveal.json payloads (kit §3).
    assert state_string(7, (4, 3), frozenset()) == "grid=7x7;self=[4, 3];barriers=[]"


def test_state_string_matches_the_kit_vector_form_with_barriers() -> None:
    assert state_string(7, (2, 4), frozenset({(1, 1)})) == "grid=7x7;self=[2, 4];barriers=[[1, 1]]"


def test_state_string_sorts_barriers_deterministically() -> None:
    a = state_string(7, (0, 0), frozenset({(2, 1), (1, 2)}))
    b = state_string(7, (0, 0), frozenset({(1, 2), (2, 1)}))
    assert a == b == "grid=7x7;self=[0, 0];barriers=[[1, 2], [2, 1]]"


def test_seal_turn_produces_a_verifiable_self_consistent_record() -> None:
    sealed = seal_turn(
        step=3,
        grid_size=7,
        position=(2, 4),
        barriers=frozenset({(1, 1)}),
        move="MOVE:N",
        intent="truth",
        hint="I drift with the crowd.",
    )
    assert sealed.payload["step"] == 3
    assert sealed.payload["state"] == "grid=7x7;self=[2, 4];barriers=[[1, 1]]"
    assert sealed.payload["position"] == [2, 4]
    assert verify(sealed.payload, sealed.nonce, sealed.commit)


def test_each_seal_uses_a_fresh_nonce() -> None:
    kwargs = {
        "step": 1,
        "grid_size": 7,
        "position": (0, 0),
        "barriers": frozenset(),
        "move": "STAY",
        "intent": "truth",
        "hint": "…",
    }
    first, second = seal_turn(**kwargs), seal_turn(**kwargs)  # type: ignore[arg-type]
    assert first.nonce != second.nonce
    assert first.commit != second.commit
