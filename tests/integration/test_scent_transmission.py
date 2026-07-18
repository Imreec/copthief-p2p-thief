"""M3-2 acceptance (PRD_scent §8): a peer-loop game transmits the locked-model trail.

Runs the full symmetric loop over the queue transports and checks every logged
outbound TurnMessage: non-empty grid, exactly one fresh center at the §2 transmitted
value, and the §2 ring values around the very first deposit (shipped config).
"""

import json
from pathlib import Path

from copthief_core.peer.match import run_local_minigame
from copthief_core.shared.config import load_all

CONSTITUTION, _PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
FRESH_CENTER = round(CONSTITUTION.pheromones.center_intensity - CONSTITUTION.pheromones.decay, 3)


def _turn_messages(log_path: Path) -> list[dict]:
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    return [event["message"] for event in events if event.get("event") == "turn"]


def test_peer_loop_game_transmits_locked_model_grids(tmp_path: Path) -> None:
    log_path = tmp_path / "scent_run.jsonl"
    result = run_local_minigame(Path("config"), police_seed=1, thief_seed=2, log_path=log_path)
    assert result.audit_ok_police_side
    assert result.audit_ok_thief_side
    messages = _turn_messages(log_path)
    assert len(messages) >= result.steps  # both sides' turns are in the shared log
    for message in messages:
        grid = message["smell_grid"]
        assert grid, f"empty smell_grid on step {message['step']} from {message['sender']}"
        fresh = [key for key, value in grid.items() if value == FRESH_CENTER]
        assert len(fresh) == 1, f"expected one fresh center, got {fresh} in {grid}"


def test_first_transmitted_grid_matches_the_locked_numeric_example(tmp_path: Path) -> None:
    log_path = tmp_path / "scent_first.jsonl"
    run_local_minigame(Path("config"), police_seed=1, thief_seed=2, log_path=log_path)
    first = _turn_messages(log_path)[0]
    grid = first["smell_grid"]
    decay = CONSTITUTION.pheromones.decay
    center_key = next(key for key, value in grid.items() if value == FRESH_CENTER)
    row, col = (int(part) for part in center_key.split(","))
    # PRD_scent §2 example: ring-1 and ring-2 transmit at (2/3 I - d) and (1/3 I - d).
    intensity = CONSTITUTION.pheromones.center_intensity
    half = CONSTITUTION.pheromones.grid_size // 2
    falloff = intensity / (half + 1)
    ring_values = {
        ring: round(round(max(0.0, intensity - falloff * ring), 3) - decay, 3) for ring in (1, 2)
    }
    board = CONSTITUTION.board
    for ring, expected in ring_values.items():
        probe = (row, col + ring)  # walk east; skip if that cell fell off the board
        if board.axis_start_index <= probe[1] < board.axis_start_index + board.grid_size:
            assert grid[f"{probe[0]},{probe[1]}"] == expected
