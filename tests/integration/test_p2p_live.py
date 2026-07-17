"""Two-process localhost match — live (spawns a subprocess + binds a socket).

Excluded from keyless CI (`-m 'not live'`); run manually:
`uv run pytest tests/integration/test_p2p_live.py -m live -q`.
The committed evidence run lives in docs/evidence/m1-p2p-match.md.
"""

from pathlib import Path

import pytest

from copthief_core.sdk.simulation import SimulationSdk


@pytest.mark.live
def test_one_command_two_process_localhost_match_self_audits_clean() -> None:
    sdk = SimulationSdk(Path("config"))
    result = sdk.run_p2p_match(
        police_seed=1, thief_seed=2, thief_port=sdk.private.my_port + 1, host="127.0.0.1"
    )
    assert result.outcome == "thief_survival"
    assert result.audit_ok_police_side
    assert result.audit_ok_thief_side
    # Police-side step count: it ends on the thief's inbound survival turn (M2 F2).
    assert result.steps == sdk.constitution.movement.survival_threshold - 1
