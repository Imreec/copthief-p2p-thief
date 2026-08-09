"""Typed views of the PRIVATE `config/game.toml` (book App B §4; PLAN §7).

Split out of `config_model` at M7-8 (150-line rule) along the file's own seam: the
signed constitution and the operational limits stay there, the per-peer settings that
never cross the wire live here. `config_model` re-exports these names, so every caller
keeps importing from one place.
"""

from __future__ import annotations

from dataclasses import dataclass

from copthief_core.shared.locked_models import LockedModelRegistry


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
class EmailSettings:
    """`[email]` (M7-6, ADR-0008): disabled with NO recipient is the resting state, and
    it survives section omission. `recipient` is a tuple because the authorization IS
    the configured recipient (friendly = us + the opponent; counted = the lecturer
    alone) — an empty tuple can reach no transport."""

    enabled: bool
    mode: str
    recipient: tuple[str, ...]
    sender: str
    token_path: str
    # The book's sole binding reporting address (§9.3). Config-owned, never in code
    # (#5); naming it is what lets the interlock refuse it outside a counted series.
    lecturer: str = ""


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
    # M7-57: the deadline on ONE outbound tool call. Distinct from every budget above,
    # which bound a whole exchange: this bounds a single delivered-but-unanswered push,
    # the case that has no other clock. Reconciled against the SIGNED
    # `response_timeout_sec` — a single attempt that can outlast the deadline the
    # opponent enforces makes a retry impossible to fit inside it.
    call_timeout_seconds: float
    # M7-8: how many steps ahead of the awaited one we buffer before calling it a
    # flood (at-least-once delivery can put two of the opponent's pushes in flight).
    inbound_buffer_limit: int
    # M7-43: how many times a window whose HANDSHAKE never completed may be retried
    # at the SAME sub-game index before the series gives up. A window that produced
    # a result (including a technical loss) spends its index and is never retried.
    handshake_retry_budget: int
    # [belief] evidence-trust tuning (PRD_belief §5) — private, never negotiated.
    smell_trust_weight: float
    hint_trust_default: float
    # M5-5 profiling floor: the shifted hint trust never drops below this
    # (distrust-but-never-eliminate — SQ3 stance).
    profile_hint_floor: float
    # M9-2: the sharp fresh-peak observation tier (0.0 = off, the pre-M9 voucher
    # path byte-for-byte). Private trust tuning like the two weights above.
    fresh_peak_trust: float
    # [strategy] brain selection per role (PLAN §7) — private, never negotiated.
    # [strategy.<role>] sub-tables carry the brain's numeric knobs (M5 weights etc.):
    # config-owned per CLAUDE.md #5, tuned offline (M5-4), never on the sparring host.
    police_class: str
    thief_class: str
    police_options: dict[str, float]
    thief_options: dict[str, float]
    # M7-15: `[strategy.<role>.<scent_model>]` overlays — tuned vectors are
    # physics-specific (the M7-14 gate comparison), so a sub-table named after a
    # scent model applies only when that model is the selected one.
    police_model_options: dict[str, dict[str, float]]
    thief_model_options: dict[str, dict[str, float]]
    # M5-6: which named template bank the verbal layer speaks ("" = the default
    # bank) — the A/B arena run ships its winner here.
    hint_bank: str
    # [scent] which named model we are willing to play (ADR-0004 v2). Private until the
    # handshake declares its HASH; the default is the reference form, so a peer that
    # never touches this section plays exactly what M3-2 shipped.
    scent_model: str
    # M6-7 audit slack, binding only for a model that does not round (M3-8).
    scent_physics_tolerance: float
    # The committed locked-model registrations (config/locked_models.json, kit SPEC §7):
    # verbatim kit docs, because the declared value is a hash over their bytes.
    locked_models: LockedModelRegistry
    # [gui] live-view render knobs (PRD_gui_replay §7) — private, display-only.
    gui: GuiSettings
    # [email] draft/arming rail (M6-4) — private; safe defaults when absent.
    email: EmailSettings
    # M7-23 (PRD_scent §10): the in-play frame validity check — ON by omission
    # (§10.6 decision 1). Defaulted so direct constructions stay valid; the loader
    # always passes it explicitly.
    frame_check: bool = True
    # M7-25: which registered `info_mode` doc we declare at negotiate (kit SPEC §7).
    # "belief" = the field reaches decisions only through the belief layer — the
    # posture the M7-23 firewall enforces; the declaration makes it a checkable lock.
    info_mode: str = "belief"
    # M7-34 league ledger (book §9.2.1): counted games played so far (declared
    # mutually at game start — the diversity weighting's input) and the opponents
    # they were played against (first-meeting derivation). Imree updates both after
    # every counted series; warm-ups never move them.
    counted_games_played: int = 0
    counted_opponents: tuple[str, ...] = ()

    def strategy_options(self, role: str) -> dict[str, float]:
        """The effective brain knobs for `role`: the base `[strategy.<role>]` table
        overlaid by the sub-table named after the SELECTED scent model (M7-15) —
        deployment follows the physics, mechanically."""
        base = self.police_options if role == "police" else self.thief_options
        per_model = self.police_model_options if role == "police" else self.thief_model_options
        return {**base, **per_model.get(self.scent_model, {})}
