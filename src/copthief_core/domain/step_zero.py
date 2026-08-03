"""Reading a peer's revealed step-0 declaration (pure — M7-33/M7-36).

One function shared by the live settlement path (peer/settlement) and the log-rebuild
path (report/summary_from_log): both read the SAME revealed records, so the commit a
report carries can never depend on which path built it — the 16:00 verification
window's defect, where the driver held the opponent's commit and the emitted artifact
said "unknown" because only the in-memory path had learned the field.
"""

from __future__ import annotations

from typing import Any

__all__ = ["revealed_commit"]


def revealed_commit(records: list[dict[str, Any]]) -> str:
    """The commit a peer's revealed step-0 declared ("unknown" absent).

    Reads both step-0 spellings — our/the reference's `system_spec` and the book
    example's `step_zero` — the field is what matters, not the label.
    """
    for record in records:
        payload = record.get("payload", {})
        if isinstance(payload, dict) and payload.get("type") in ("system_spec", "step_zero"):
            value = payload.get("github_commit")
            return str(value) if value else "unknown"
    return "unknown"
