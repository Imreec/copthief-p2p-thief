"""The official Hebrew report (book §8; PRD_reporting §2 D2): sign-then-insert.

The consensus signature is computed over the report BEFORE the
``חתימת_קונסנזוס_משותפת`` key is inserted — a verifier pops the key and re-hashes.
"""

from __future__ import annotations

from report_fixtures import make_summary

import copthief_core
from copthief_core.report.consensus import consensus_signature
from copthief_core.report.hebrew import RESULT_HEBREW, build_report

TERMS = {"rules": {"max_steps": 35}, "setting": "New York"}


def test_result_vocabulary_matches_the_reference_constants() -> None:
    assert RESULT_HEBREW["capture"] == "לכידה"
    assert RESULT_HEBREW["survival"] == "הישרדות"
    assert RESULT_HEBREW["timeout"] == "תוצאה_טכנית"
    assert RESULT_HEBREW["tamper_forfeit"] == "פסילת_זיוף"


def test_report_signature_is_sign_then_insert() -> None:
    report = build_report(make_summary(), TERMS)
    signature = report.pop("חתימת_קונסנזוס_משותפת")
    assert signature == consensus_signature(report)


def test_report_translates_result_and_passes_unknown_through() -> None:
    assert build_report(make_summary(result="capture"), TERMS)["תוצאה"] == "לכידה"
    assert build_report(make_summary(result="weird"), TERMS)["תוצאה"] == "weird"


def test_report_code_version_is_ours_and_terms_ride_verbatim() -> None:
    report = build_report(make_summary(), TERMS)
    assert report["גרסת_קוד"] == copthief_core.__version__
    assert report["הסכם_תפאורה_משא_ומתן"] == TERMS
    assert report["תפקיד_מדווח"] == "thief"
    assert report["הסכמה_הדדית"] is True


def test_step_log_merges_history_into_hebrew_keys() -> None:
    summary = make_summary(steps=2)
    rows = build_report(summary, TERMS)["לוג_צעדים_מאומת"]
    assert len(rows) == 2
    first, entry = rows[0], summary["history"][0]
    assert first["מספר_צעד"] == entry["step"]
    assert first["רמז_מילולי_שנשלח"] == entry["hint"]
    assert first["גריד_ריח_מצורף"] == entry["smell_grid"]
    assert first["מחסום_שהוצב"] == entry["barrier_placed"]
    assert first["חתימת_מצב"] == entry["commit"]


def test_spec_declaration_reads_the_sealed_step0_record() -> None:
    summary = make_summary(tokens_total=42)
    block = build_report(summary, TERMS)["הצהרת_מפרט_מחשב_וטוקנים"]
    assert block["מפרט_מחשב"] == summary["records"][0]["payload"]["spec"]
    assert block["דגם_שפה_בשימוש"] == "none"
    assert block["גרסת_קוד"] == "1.00"
    assert block["סך_טוקנים_שנצרכו"] == 42


def test_spec_declaration_degrades_when_no_step0_record_exists() -> None:
    summary = make_summary()
    summary["records"] = summary["records"][1:]  # drop the system_spec record
    block = build_report(summary, TERMS)["הצהרת_מפרט_מחשב_וטוקנים"]
    assert block["מפרט_מחשב"] == {}
    assert block["דגם_שפה_בשימוש"] == "unknown"
