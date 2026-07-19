"""M6-4 `[email]` private config (constraint #16): draft default, mechanically.

The shipped game.toml carries the section explicitly; a TOML WITHOUT it still
loads with the safe defaults (enabled=false, mode="draft") — the interlock's
resting state can never be configured away by omission.
"""

from __future__ import annotations

from pathlib import Path

from copthief_core.shared.config import load_private_settings

SHIPPED = Path("config") / "game.toml"


def test_shipped_toml_defaults_to_disabled_draft() -> None:
    private = load_private_settings(SHIPPED)
    assert private.email.enabled is False
    assert private.email.mode == "draft"
    assert private.email.token_path  # a concrete git-ignored path, never empty


def test_toml_without_an_email_section_gets_the_safe_defaults(tmp_path: Path) -> None:
    # The shipped file keeps [email] as its LAST section, so "absent" is a clean cut.
    text = SHIPPED.read_text(encoding="utf-8").split("\n[email]")[0]
    assert "\n[email]" not in text  # no section HEADER left (a comment may mention it)
    path = tmp_path / "game.toml"
    path.write_text(text, encoding="utf-8")
    private = load_private_settings(path)
    assert private.email.enabled is False
    assert private.email.mode == "draft"
    assert private.email.recipient == ""


def test_email_section_values_load(tmp_path: Path) -> None:
    text = SHIPPED.read_text(encoding="utf-8").split("\n[email]")[0] + (
        '\n[email]\nenabled = true\nmode = "send"\nrecipient = "lect@example.test"\n'
        'sender = "team@example.test"\ntoken_path = "secrets/token.json"\n'
    )
    path = tmp_path / "game.toml"
    path.write_text(text, encoding="utf-8")
    email = load_private_settings(path).email
    assert email.enabled is True
    assert email.mode == "send"
    assert email.recipient == "lect@example.test"
    assert email.sender == "team@example.test"
    assert email.token_path == "secrets/token.json"
