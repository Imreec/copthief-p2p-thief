"""Sparring-host safety guard (M7-1; ADR-0008 decision 6, deferred there until the host).

Two standing rules govern any peer we stand up for someone else to practise against:

* **the generic brain only — tuned weights never deploy there** (CLAUDE.md §9/§10). A
  sparring peer that answers with our tuned brain hands a future counted opponent a free
  sample of the thing that is being graded;
* **it cannot send mail.** The resting posture is `enabled=false` with NO recipient, and
  the recipient is the authorization (ADR-0008), so an address on a standing host is the
  one thing that must not be there — a host carrying one is a single flag from sending.

Both are properties of a loaded config, so neither has to be remembered. This module is
the check; `scripts/make_sparring_config.py` derives a config that passes it, and the CLI
refuses to play a `--sparring` peer that does not.
"""

from __future__ import annotations

from copthief_core.shared.config_model import PrivateSettings


class SparringUnsafeError(RuntimeError):
    """The config offered for a sparring host breaks a standing deployment rule."""


def sparring_problems(private: PrivateSettings) -> list[str]:
    """Every standing-rule violation in `private` (Input: loaded private settings;
    Output: the problems, empty when the config is safe to stand up)."""
    problems: list[str] = []
    for role, options in (("police", private.police_options), ("thief", private.thief_options)):
        if options:
            problems.append(
                f"[strategy.{role}] carries {len(options)} tuned weight(s) "
                f"({', '.join(sorted(options))}): tuned weights never deploy to a sparring host"
            )
    if private.email.enabled:
        problems.append("[email] enabled=true: a sparring host never sends mail")
    if private.email.recipient:
        problems.append(
            f"[email] recipient is set ({len(private.email.recipient)} address(es)): "
            "the recipient is the authorization, so a sparring host carries none"
        )
    return problems


def assert_sparring_safe(private: PrivateSettings) -> None:
    """Refuse a config that may not be stood up for an opponent to practise against
    (Input: loaded private settings; Output: none; Raises: SparringUnsafeError listing
    EVERY violation at once — the App F guard's habit, because a config is fixed in one
    pass or not at all)."""
    problems = sparring_problems(private)
    if problems:
        raise SparringUnsafeError("config is not safe for a sparring host:\n" + "\n".join(problems))
