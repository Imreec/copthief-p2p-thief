"""Typed views of the three config files (book App B; PLAN §7). Pure declarations — no I/O.

`Constitution` mirrors the signed `config/game.json` section-for-section; `PrivateSettings`
mirrors the per-peer `config/game.toml`; `RateLimits` mirrors `config/rate_limits.json`.
Every quantitative value flows from those files through these types — never from literals.
"""

from __future__ import annotations

from dataclasses import dataclass

from copthief_core.domain.board import Board, Coord
from copthief_core.domain.scoring import ScoringTable


@dataclass(frozen=True)
class BoardParams:
    """`board_and_agents`: grid side, roster size, axis contract, starts."""

    grid_size: int
    num_agents: int
    thief_start: Coord
    cop_start: Coord
    axis_origin_corner: str
    axis_start_index: int

    def make_board(self) -> Board:
        """A fresh (barrier-free) board under the signed axis contract."""
        return Board(
            grid_size=self.grid_size,
            axis_origin_corner=self.axis_origin_corner,
            axis_start_index=self.axis_start_index,
        )


@dataclass(frozen=True)
class WorldParams:
    """`world`: the real-world hint arena and the verbal-hint word cap."""

    map_area: str
    hint_max_words: int


@dataclass(frozen=True)
class MovementParams:
    """`movement_and_barriers`: the signed move alphabet, quotas, and step caps."""

    move_set: tuple[str, ...]
    max_barriers: int
    max_moves: int
    survival_threshold: int


@dataclass(frozen=True)
class PheromoneParams:
    """`pheromones`: emission intensity, per-step decay, emission window side, and the
    reference-only emission gate (kit §5; sourced from the App F table default when the
    signed file omits it — PRD_crypto §8.2)."""

    center_intensity: float
    decay: float
    grid_size: int
    min_center_intensity: float


@dataclass(frozen=True)
class LeagueParams:
    """`network_and_league`: timeouts and the league bookkeeping constants."""

    response_timeout_sec: int
    watchdog_timeout_sec: int
    num_games: int
    diversity_reward: int
    min_games_to_pass: int
    max_games_per_team: int
    token_budget_per_series: int


@dataclass(frozen=True)
class GatekeeperParams:
    """`rate_limiter_gatekeeper`: the signed operational minimums (App F table 19)."""

    requests_per_minute: int
    concurrent_requests: int
    retry_backoff_sec: int
    max_retries: int
    queue_depth: int


@dataclass(frozen=True)
class Constitution:
    """The signed shared `config/game.json` — byte-identical between the two peers."""

    schema_version: str
    agreed_between: tuple[str, str]
    board: BoardParams
    world: WorldParams
    movement: MovementParams
    scoring: ScoringTable
    pheromones: PheromoneParams
    league: LeagueParams
    gatekeeper: GatekeeperParams


@dataclass(frozen=True)
class GuiSettings:
    """`[gui]`: live-view render knobs (PRD_gui_replay §7) — private, display-only.

    `heat_low`/`heat_high` are the '#rrggbb' heatmap anchors at p=0 / p=1; the theme
    block styles the window chrome (dark slate by default)."""

    refresh_ms: int
    cell_px: int
    heat_low: str
    heat_high: str
    png_dpi: int
    font_family: str
    font_size: int
    theme_bg: str
    theme_panel: str
    theme_fg: str
    accent: str


@dataclass(frozen=True)
class PrivateSettings:
    """The per-peer `config/game.toml` — never crosses the wire, never negotiated."""

    version: str
    group_name: str
    group_id: str
    sub_game_number: int
    # Group identity block (F8b): exchanged in the handshake because the reference's
    # declaration writer requires every key; spec fills at M6-3 (shared/sysinfo).
    members: tuple[str, ...]
    repos: dict[str, str]
    mcp_servers: dict[str, str]
    llm_model: str
    my_port: int
    opponent_url: str
    turn_timeout_seconds: float
    poll_interval_seconds: float
    connect_timeout_seconds: float
    # [belief] evidence-trust tuning (PRD_belief §5) — private, never negotiated.
    smell_trust_weight: float
    hint_trust_default: float
    # [strategy] brain selection per role (PLAN §7) — private, never negotiated.
    # [strategy.<role>] sub-tables carry the brain's numeric knobs (M5 weights etc.):
    # config-owned per CLAUDE.md #5, tuned offline (M5-4), never on the sparring host.
    police_class: str
    thief_class: str
    police_options: dict[str, float]
    thief_options: dict[str, float]
    # [gui] live-view render knobs (PRD_gui_replay §7) — private, display-only.
    gui: GuiSettings


@dataclass(frozen=True)
class RateLimits:
    """`config/rate_limits.json` — operational limits, each ≥ its signed minimum."""

    version: str
    requests_per_minute: int
    concurrent_requests: int
    retry_backoff_sec: int
    max_retries: int
    queue_depth: int
