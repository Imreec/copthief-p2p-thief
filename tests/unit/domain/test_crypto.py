"""domain/crypto behaviors beyond the kit fixtures: tamper detection, nonce policy (ch.5)."""

from copthief_core.domain.crypto import (
    canonical_bytes,
    commit,
    game_uid,
    make_nonce,
    terms_signature,
    verify,
)


def test_canonical_bytes_are_key_order_invariant() -> None:
    assert canonical_bytes({"b": 1, "a": 2}) == canonical_bytes({"a": 2, "b": 1})


def test_series_game_id_is_the_sorted_pair_from_either_side() -> None:
    """M7-17: the reference DERIVES game_id by sorting the pair (`domain/game_ids.py`:
    `pair = sorted([group_a, group_b])`), so both peers get one string with no
    convention to settle — kit SPEC §4 pins it beside game_uid. Our self-first form is
    what produced the friendly's cosmetic report mismatch (2026-07-26 diff)."""
    from copthief_core.domain.crypto import series_game_id

    assert series_game_id("imreeyal", "anrbj666") == "anrbj666-vs-imreeyal"
    assert series_game_id("anrbj666", "imreeyal") == "anrbj666-vs-imreeyal"


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


def test_equivalent_float_literals_verify_same_double_same_bytes() -> None:
    # League coordination 2026-07-18, corrected: 0.10000000000000001 IS 0.1 (the same
    # IEEE double), so both literal forms canonicalize to "0.1" and the signature
    # VERIFIES - equivalent-literal drift is a non-problem by construction.
    terms = {"pheromone_decay": 0.1}
    nonce = make_nonce()
    signature = terms_signature(terms, nonce)
    assert 0.10000000000000001 == 0.1  # noqa: PLR0133 - the point being pinned
    assert terms_signature({"pheromone_decay": 0.10000000000000001}, nonce) == signature


def test_distinct_double_float_drift_breaks_the_terms_signature() -> None:
    # The REAL drift case (Alon's dict-equality note, sharpened): a genuinely distinct
    # double - e.g. an accumulated 0.1+0.2 - serializes as 0.30000000000000004, so the
    # canonical bytes differ and the handshake signature gate refuses the terms.
    nonce = make_nonce()
    clean = terms_signature({"pheromone_decay": 0.3}, nonce)
    drifted = terms_signature({"pheromone_decay": 0.1 + 0.2}, nonce)
    assert clean != drifted
