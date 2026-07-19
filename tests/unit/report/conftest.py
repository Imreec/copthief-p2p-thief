"""Shared fixtures for the report-layer unit tests (M6-2); helpers in report_fixtures."""

from __future__ import annotations

from typing import Any

import pytest

from copthief_core.domain.scoring import ScoringTable


@pytest.fixture
def table() -> ScoringTable:
    """The App-F-shaped scoring table with distinct, test-legible values."""
    return ScoringTable(
        capture_cop=20,
        capture_thief=5,
        survival_cop=5,
        survival_thief=10,
        tie_score=2,
        technical_loss=0,
    )


@pytest.fixture
def shared_terms() -> dict[str, Any]:
    """A minimal signed-config dict (the sections the artifact builders touch)."""
    return {
        "agreed_between": ["team-a", "team-b"],
        "board_and_agents": {"grid_size": 7},
        "scoring": {
            "capture_cop": 20,
            "capture_thief": 5,
            "survival_cop": 5,
            "survival_thief": 10,
            "tie_score": 2,
        },
        "network_and_league": {"num_games": 2, "token_budget_per_series": 200000},
    }
