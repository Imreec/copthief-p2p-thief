"""M0 smoke: packages import and carry the mandated starting version (CLAUDE.md §1 rule 9)."""

import copthief_core
import copthief_thief


def test_core_version_starts_at_1_00() -> None:
    assert copthief_core.__version__ == "1.00"


def test_role_package_version_starts_at_1_00() -> None:
    assert copthief_thief.__version__ == "1.00"
