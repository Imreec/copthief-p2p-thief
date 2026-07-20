"""M7-6 `[email]` private config (ADR-0008): no recipient is the resting state.

The shipped game.toml carries the section explicitly; a TOML WITHOUT it still loads
disabled and with NO recipient — and since the authorization IS the recipient, the
resting state can never be configured away by omission.
"""

from __future__ import annotations

from pathlib import Path

from copthief_core.shared.config import load_private_settings

SHIPPED = Path("config") / "game.toml"


def test_shipped_toml_ships_disabled_with_no_recipient() -> None:
    private = load_private_settings(SHIPPED)
    assert private.email.enabled is False
    assert private.email.recipient == ()  # nothing to send to = nothing can be sent
    assert private.email.token_path  # a concrete git-ignored path, never empty


def test_toml_without_an_email_section_gets_the_safe_defaults(tmp_path: Path) -> None:
    # The shipped file keeps [email] as its LAST section, so "absent" is a clean cut.
    text = SHIPPED.read_text(encoding="utf-8").split("\n[email]")[0]
    assert "\n[email]" not in text  # no section HEADER left (a comment may mention it)
    path = tmp_path / "game.toml"
    path.write_text(text, encoding="utf-8")
    private = load_private_settings(path)
    assert private.email.enabled is False
    assert private.email.recipient == ()


def test_recipient_list_loads_for_the_friendly_report_exchange(tmp_path: Path) -> None:
    """Friendly = us + the opponent team; counted = the lecturer alone."""
    text = SHIPPED.read_text(encoding="utf-8").split("\n[email]")[0] + (
        '\n[email]\nenabled = true\nmode = "send"\n'
        'recipient = ["team@example.test", "peer.team@example.test"]\n'
        'sender = "team@example.test"\ntoken_path = "secrets/token.json"\n'
    )
    path = tmp_path / "game.toml"
    path.write_text(text, encoding="utf-8")
    email = load_private_settings(path).email
    assert email.enabled is True
    assert email.mode == "send"
    assert email.recipient == ("team@example.test", "peer.team@example.test")
    assert email.sender == "team@example.test"
    assert email.token_path == "secrets/token.json"


def test_a_bare_string_recipient_still_loads(tmp_path: Path) -> None:
    """One address needs no brackets — the common counted-series shape."""
    text = SHIPPED.read_text(encoding="utf-8").split("\n[email]")[0] + (
        '\n[email]\nenabled = true\nrecipient = "lecturer@example.test"\n'
    )
    path = tmp_path / "game.toml"
    path.write_text(text, encoding="utf-8")
    assert load_private_settings(path).email.recipient == ("lecturer@example.test",)


def test_blank_recipients_are_dropped_not_carried(tmp_path: Path) -> None:
    """A blank address must not look like authorization to the interlock."""
    text = SHIPPED.read_text(encoding="utf-8").split("\n[email]")[0] + (
        '\n[email]\nenabled = true\nrecipient = ["", "  "]\n'
    )
    path = tmp_path / "game.toml"
    path.write_text(text, encoding="utf-8")
    assert load_private_settings(path).email.recipient == ()
