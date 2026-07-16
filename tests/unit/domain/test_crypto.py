"""domain/crypto behaviors beyond the kit fixtures: tamper detection, nonce policy (ch.5)."""

from copthief_core.domain.crypto import (
    canonical_bytes,
    commit,
    game_uid,
    make_nonce,
    verify,
)


def test_canonical_bytes_are_key_order_invariant() -> None:
    assert canonical_bytes({"b": 1, "a": 2}) == canonical_bytes({"a": 2, "b": 1})


def test_canonical_bytes_keep_hebrew_native_utf8() -> None:
    assert "אני".encode() in canonical_bytes({"hint": "אני ליד הכיכר"})


def test_verify_fails_on_any_payload_mutation() -> None:
    payload = {"step": 3, "move": "MOVE:N", "intent": "truth", "hint": "by the docks"}
    nonce = make_nonce()
    sealed = commit(payload, nonce)
    assert verify(payload, nonce, sealed)
    assert not verify({**payload, "move": "MOVE:S"}, nonce, sealed)
    assert not verify({**payload, "intent": "lie"}, nonce, sealed)


def test_verify_fails_on_a_wrong_nonce() -> None:
    payload = {"step": 1, "move": "STAY"}
    sealed = commit(payload, make_nonce())
    assert not verify(payload, make_nonce(), sealed)


def test_nonces_are_32_hex_chars_and_unique() -> None:
    nonces = {make_nonce() for _ in range(64)}
    assert len(nonces) == 64
    assert all(len(n) == 32 and set(n) <= set("0123456789abcdef") for n in nonces)


def test_nonce_source_is_the_secrets_module_never_random() -> None:
    # App E / book ch.5: nonces come from `secrets`; `random` must not even be imported.
    import copthief_core.domain.crypto as crypto_module

    source = open(crypto_module.__file__, encoding="utf-8").read()  # noqa: SIM115, PTH123
    assert "import secrets" in source
    assert "import random" not in source


def test_game_uid_is_sensitive_to_terms_but_not_group_order() -> None:
    terms = {"board_size": 7, "num_games": 1}
    assert game_uid(terms, "g-a", "g-b") == game_uid(terms, "g-b", "g-a")
    assert game_uid(terms, "g-a", "g-b") != game_uid({**terms, "board_size": 9}, "g-a", "g-b")
