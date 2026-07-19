"""The official Hebrew match report (book §8; PRD_reporting §2 D2).

Schema follows the book, scoped to one sub-game; keys interface-mirrored from the
reference @960499fd (ADR-0002). The consensus signature is computed over the report
BEFORE ``חתימת_קונסנזוס_משותפת`` is inserted (sign-then-insert — Alon's find): a
verifier pops the key and re-hashes the remainder. Written to disk beside the four
reference artifacts (`report_<game_id>_g<NN>.json`); the emailed body stays the
English result artifact (D2, reference-mirrored).
"""

from __future__ import annotations

from typing import Any

from copthief_core import __version__ as code_version
from copthief_core.report.consensus import consensus_signature

RESULT_HEBREW = {
    "capture": "לכידה",
    "survival": "הישרדות",
    "timeout": "תוצאה_טכנית",
    "tamper_forfeit": "פסילת_זיוף",
}


def _step_log(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """The book's verified step-log rows from the inbound message history."""
    return [
        {
            "מספר_צעד": message["step"],
            "טביעת_זמן": message["timestamp"],
            "שולח": message["sender"],
            "רמז_מילולי_שנשלח": message["hint"],
            "גריד_ריח_מצורף": message["smell_grid"],
            "מחסום_שהוצב": message["barrier_placed"],
            "חתימת_מצב": message["commit"],
        }
        for message in summary["history"]
    ]


def _spec_declaration(summary: dict[str, Any]) -> dict[str, Any]:
    """Hardware + model + token declaration, read from the SEALED step-0 record so it
    is audit-verified like every move (book §6/§8; M6-3 owns writing that record)."""
    spec_payload: dict[str, Any] = next(
        (
            r["payload"]
            for r in summary.get("records", [])
            if r["payload"].get("type") == "system_spec"
        ),
        {},
    )
    return {
        "מפרט_מחשב": spec_payload.get("spec", {}),
        "דגם_שפה_בשימוש": spec_payload.get("model", "unknown"),
        "גרסת_קוד": spec_payload.get("code_version", code_version),
        "סך_טוקנים_שנצרכו": summary.get("tokens_total", 0),
    }


def build_report(summary: dict[str, Any], terms: dict[str, Any]) -> dict[str, Any]:
    """The official report from THIS peer's perspective (audit-verified inputs).

    Input: a reference-shaped sub-game summary + the translated signed terms.
    Output: the Hebrew-keyed report dict, consensus-signed sign-then-insert.
    """
    report: dict[str, Any] = {
        "סוג_דוח": "משחק_ליגה_רשמי",
        "גרסת_קוד": code_version,
        "תפקיד_מדווח": summary["role"],
        "קבוצה_מדווחת": summary.get("group_name", "unnamed"),
        "מספר_משחקון": summary.get("sub_game_number", 1),
        "זמן_התחלה": summary.get("started_at", ""),
        "משך_משחק_שניות": summary.get("duration_seconds", 0),
        "הצהרת_מפרט_מחשב_וטוקנים": _spec_declaration(summary),
        "תוצאה": RESULT_HEBREW.get(summary["result"], summary["result"]),
        "מנצח": summary["winner"],
        "צעדים_שבוצעו": summary["steps"],
        "הסכם_תפאורה_משא_ומתן": terms,
        "אימות_קריפטוגרפי": {
            "צעדים_מאומתים": summary["audit"]["verified_steps"],
            "צעדים_שנכשלו": summary["audit"]["failed_steps"],
        },
        "לוג_צעדים_מאומת": _step_log(summary),
        "הצהרות_חתומות_שלי": summary["records"],
        "הסכמה_הדדית": summary["audit"]["passed"],
    }
    report["חתימת_קונסנזוס_משותפת"] = consensus_signature(report)
    return report
