# PRD — Game engine (mechanism PRD, milestone M1)

> **Status: APPROVED (gate M1-1, 2026-07-16; §6.1 terminology sharpened per Imree's review —
> a counted match = a series of exactly six mini-games, fixed).** **This copy: the thief repo** —
> the engine mechanism is role-agnostic core, authored and reviewed in the police (lead) repo
> (ADR-0001 docs convention); content identical apart from this note. Parent docs: `docs/PRD.md` FR-1/FR-4,
> `docs/PLAN.md` §3–§5, §7. Sources of truth: book v3.0.0 ch.3 (physics/scoring) + App B (config
> schema) + App F (binding parameters table) > this document. **Every number below is shown as its
> binding `game.json` key; nothing quantitative is hardcoded — the App F transcription itself ships
> as a data file, not as Python literals (constraint #5).**
> Covers TODO **M1-2** (board, rules, scoring + App F guard) and **M1-4** (state machine).

## 1. Scope & non-goals

**In scope (M1):** `copthief_core/domain/` — board geometry, action legality, barrier rules,
capture/end-condition resolution, mini-game + series scoring; the game state machine
(PLAN §5); `copthief_core/shared/config` — loader for `game.json`/`game.toml`/`rate_limits.json`
with the **App F validation guard** (constraint #15).
**Non-goals:** scent & belief (M3, own PRD) · brains beyond the M1 geometric stub (M5) · wire/MCP
(PRD_crypto pins bytes; M1-5/M1-6 build transport) · GUI/replay (M4) · reporting artifacts (M6).

## 2. Physics requirements (book ch.3; App E iron rules)

**E-1 Board & coordinates.** Square grid of side `grid_size`. A cell is `(row, col)`;
`axis_origin_corner` fixes which corner is `(axis_start_index, axis_start_index)` (default
top-left, vertical axis growing downward); `axis_start_index` sets where counting starts. Both are
negotiable but **must match between peers or the race falls apart** — they are part of the signed
terms. Starts come from `thief_start` / `cop_start` (negotiable; defaults center/corner).

**E-2 Actions & legality.** Per turn an agent makes exactly one move from `move_set` (fixed:
N/E/S/W one cell, or STAY); diagonals are illegal. Physics is enforced **by the opposing agent**
(no referee): the engine validates our own candidate action *and* every inbound opponent claim
against the same rules module. An illegal inbound move is a protocol violation (state machine →
TECHNICAL_LOSS path, never silent acceptance).

**E-3 Barriers (cop only).** In a turn where the cop forgoes movement he may place one barrier on
his own cell or one of its four orthogonal neighbors. A barrier is irreversible and impassable to
**both** players for the rest of the mini-game. Quota: `max_barriers` per mini-game. Every
placement is truthfully and publicly declared (location included) — hidden or misdeclared barriers
are cheating, exposed at audit. Placement is resource management: the engine only enforces
legality + quota; *where* to place is strategy (M5).

**E-4 Capture & end conditions.** A mini-game ends by exactly one of:
1. **Capture by landing** — the cop moves onto the thief's cell and declares a Capture Claim; the
   thief is cryptographically obliged to answer truthfully (lie ⇒ audit forfeit).
2. **Capture by barrier** — a barrier placed on the thief's current cell captures immediately.
3. **Imprisonment** — a thief with no legal escape (all four orthogonal neighbors blocked by
   barriers and/or board edges) counts as captured. (STAY does not rescue an imprisoned thief —
   the book defines imprisonment purely by blocked neighbors.)
4. **Survival** — the thief survives `survival_threshold` valid steps without capture.
5. **Step cap** — `max_moves` caps the mini-game length (defaults coincide with
   `survival_threshold`; the guard keeps `max_moves ≥ survival_threshold` unnecessary — both are
   independent App F minimums and are validated independently).
6. **Technical loss** — crash, deadline exhaustion, or cryptographic forgery: **0/0 for both
   sides** (`technical_loss`).

**E-5 Scoring (all values fixed by App F).** Capture → `capture_cop` / `capture_thief`; survival →
`survival_cop` / `survival_thief`; technical loss → `technical_loss` for both. **Series scoring:**
a counted series is `num_games` mini-games; totals are **derived from per-mini-game results, never
declared** (PRD FR-11 / kit §6). If the series aggregate against an opponent ties, each side
scores `tie_score`. The scoring module exposes both per-mini-game resolution and series
aggregation as pure functions.

**E-6 One rules module, two modes (PLAN §3).** The rules module is pure and full-information: it
answers "is this action legal given board+barriers+positions" and "what ended the game." *Referee
mode* (tests/arena/tuning) calls it with both true positions. *Peer mode* (live) calls it with our
position + the opponent's **claims**, deferring truth to commit-reveal + audit. No rule logic is
duplicated between modes.

## 3. State machine (PLAN §5, TODO M1-4)

Exactly the PLAN §5 transition table: WAITING_FOR_OPPONENT → COMPUTING_MOVE → COMMITTING →
AWAITING_REVEAL → VERIFYING → {WAITING_FOR_OPPONENT | GAME_OVER}; any communication state →
TECHNICAL_LOSS on deadline exhaustion / illegal transition / protocol violation. Implementation:
an explicit transition table (frozen mapping); any transition not in the table **raises**
immediately (bug surfaces in dev, never a silent freeze). Terminal: GAME_OVER (→ audit),
TECHNICAL_LOSS (→ persistence + controlled shutdown; the watchdog seam lands M1-6).

## 4. Binding parameters (App F transcription — the guard's data file)

The loader validates every `game.json` against this table (shipped as
`config/app_f_table.json`, our transcription of App F; the book's table is the authority — any
discrepancy found later is fixed in the data file, never in code):

| `game.json` key | App F status | Default (= example value) |
|---|---|---|
| `board_and_agents.grid_size` | minimum | 7 |
| `board_and_agents.num_agents` | fixed | 2 |
| `board_and_agents.axis_origin_corner` | negotiable | "top-left" |
| `board_and_agents.axis_start_index` | negotiable | 0 |
| `board_and_agents.thief_start` | negotiable | [3, 3] |
| `board_and_agents.cop_start` | negotiable | [0, 0] |
| `world.map_area` | negotiable | "New York" ("" ⇒ generic landmarks) |
| `world.hint_max_words` | negotiable | 15 |
| `movement_and_barriers.move_set` | fixed | ["N","E","S","W","STAY"] |
| `movement_and_barriers.max_barriers` | minimum | 14 |
| `movement_and_barriers.max_moves` | minimum | 35 |
| `movement_and_barriers.survival_threshold` | minimum | 35 |
| `scoring.capture_cop` / `capture_thief` | fixed | 20 / 5 |
| `scoring.survival_cop` / `survival_thief` | fixed | 5 / 10 |
| `scoring.tie_score` / `technical_loss` | fixed | 2 / 0 |
| `pheromones.pheromone_center_intensity` | fixed | 0.9 |
| `pheromones.pheromone_decay` | fixed | 0.10 |
| `pheromones.pheromone_grid_size` | fixed | 5 |
| `network_and_league.num_games` | fixed (league series) | 6 — see §6 |
| `network_and_league.diversity_reward` | fixed | 10 |
| `network_and_league.min_games_to_pass` | fixed | 2 |
| `network_and_league.max_games_per_team` | fixed | 10 |
| `network_and_league.token_budget_per_series` | negotiable | 200000 |
| `network_and_league.response_timeout_sec` | negotiable | 30 |
| `network_and_league.watchdog_timeout_sec` | negotiable | 60 |
| `rate_limiter_gatekeeper.requests_per_minute` | minimum | 30 |
| `rate_limiter_gatekeeper.concurrent_requests` | minimum | 2 |
| `rate_limiter_gatekeeper.retry_backoff_sec` | minimum | 5 |
| `rate_limiter_gatekeeper.max_retries` | minimum | 3 |
| `rate_limiter_gatekeeper.queue_depth` | minimum | 100 |

## 5. App F guard (constraint #15 — refusal semantics)

Per App F's status definitions: **fixed** — any deviation from the default ⇒ **refuse to load or
sign** (deviation disqualifies the team). **minimum** — a value below the default ⇒ refuse; at or
above ⇒ accept (negotiation may only make the game harder, never ease below the example value);
absent explicit agreement the default **is** the value the code uses. **negotiable** — any agreed
value accepted; absent agreement, the default is used. The guard runs at every load (startup,
negotiation, per-game config) and its refusal is loud and logged — it is the mechanical
implementation of "the agreed contract is a floor, not a ceiling" (book §3.2). It also asserts
`rate_limits.json` (private, operational) **meets or exceeds** the signed
`rate_limiter_gatekeeper` block on every shared key (PRD FR-9 precedence rule).

## 6. Documented interpretations (academic-freedom clause)

1. **`num_games` — terminology first, then the apparent 1-vs-6 conflict.** The book's units: a
   **mini-game** (משחקון) is one hidden-position pursuit to a scored ending; a **match** (the
   counted series vs one opponent) is `num_games` consecutive mini-games; and
   `min_games_to_pass` / `max_games_per_team` count *matches vs distinct opponents*, not
   mini-games. App F table 18 fixes `num_games` at 6 — **a counted match is always exactly six
   mini-games, non-negotiable** (confirmed at the M1-1 review). The App B listing's
   `"num_games": 1` is not a competing default: the book's own note under the listing explains it
   as the single-sample exchange illustrating the file format, the full league series requiring
   the table value. **Guard behavior:** for a counted series, `num_games ≠ 6` is refused like any
   other fixed-value deviation; dev runs and friendlies (format-free, reports never leave draft)
   may run shorter series without weakening any counted guarantee.
2. **Barrier on own cell.** Ch.3 explicitly allows placing on the cop's own cell. **Choice:** the
   cop may stand where he placed; the cell is impassable thereafter (he may leave, never
   re-enter; the thief may never enter). Verified against the reference at M2 (SQ2-adjacent).
3. **Imprisonment ignores STAY** — defined purely by blocked orthogonal neighbors (§2 E-4.3).
4. **Capture-claim cost/limits are undefined in ch.3** — that is exactly SQ2 (M2-3); the M1 engine
   resolves claims truthfully in referee mode and defers the cost model to the SQ2 answer.

## 7. Test plan (TDD; DoD of M1-2/M1-4)

Unit (happy + error, per rule): legality of all five moves incl. edges/barriers · diagonal
rejected · barrier legality (self + 4-adjacent only, quota, on-blocked-cell, irreversibility) ·
capture by landing+claim · capture by barrier · imprisonment (corner, wall, full-ring; STAY
irrelevance) · survival at exactly `survival_threshold` · step cap · scoring table incl. 0/0 ·
series aggregation + tie rule. State machine: property tests — every transition not in the table
raises; every in-table transition succeeds; terminal states absorb. Guard: per status class —
fixed-deviation refused, below-minimum refused, at/above-minimum accepted, negotiable accepted,
defaults applied absent agreement, `rate_limits.json` precedence asserted. Coverage ≥ 90%
(deterministic core), files ≤ 150 lines, `mypy --strict`, ruff clean.

## 8. Acceptance criteria (binary)

- All §7 tests green in keyless CI; domain remains I/O-free (no clock/network/files).
- The guard demonstrably refuses: a fixed-value change, a lowered minimum, and an
  under-minimum `rate_limits.json` — each observed in a test.
- A referee-mode scripted mini-game (two geometric stubs) reaches each of the four scored
  endings (capture-landing, capture-barrier, imprisonment, survival) in tests.
