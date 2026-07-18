# PRD — ThiefBrain (mechanism PRD, milestone M5) ⚑ thief repo

> **Status: DRAFT (gate M5-1, awaiting Imree's approval).** Parent docs: `docs/PRD.md` FR-6/FR-12
> + §2, `docs/PLAN.md` §8 + §13 M5. Sources of truth: book ch.6 (strategy module, pp.57–68) · M2
> spike SQ2/SQ3 · reference `domain/brains.py` @960499fd (**oracle only**, ADR-0002) · ADR-0005
> (strategy track: belief+search, lands with the M5-1 gate in the police repo). Covers TODO
> **M5-3** + the thief-led part of **M5-6** (template-bank A/B rides this brain's deception
> seam). Sibling: `docs/PRD_police_brain.md` in
> [copthief-p2p-cop](https://github.com/Imreec/copthief-p2p-cop) — the two PRDs are approved
> together; its §2–§4 (reference-heuristic re-derivation, Decision seam, arena scenario suite,
> per-role rosters) are **core groundwork built in the police repo and synced here**; this PRD
> does not restate them, it binds this repo to them.

## 1. Scope, role split, non-goals

**Role split (⚑):** `ThiefBrain` lives in `src/copthief_thief/` — this repo's own package,
**never mirrored** (ADR-0001): built here, tested here under `tests/role/` (per-repo; mirrored
test trees never name role files — PR #29 lesson). Core changes it depends on (Decision seam,
`ref-police` arena opponent, scenario suite, per-role rosters) are **police-lead**: they arrive
via sync commits, never edited here (CLAUDE.md #14). The thief has no barrier action — its
`Decision`s are always moves; the seam's barrier arm is police-only by the barrier law.

**In scope (M5-3):** `copthief_thief.brain` — region-survival move policy + articulation
awareness + **deception timing** (the M3-4 lie *mechanism* — gazetteer templates, sealed intent
flag — finally gets its *policy*: when to lie, when to spend truth); the self-mirror estimator
(§3); DoD evidence vs `ref-police` + champion-pin update in **this** repo's
`config/arena_champion.json`.

**Non-goals:** scent/belief internals — **M3-8 blocked** (brains read `BeliefFilter`'s public
surface only; the self-mirror in §3 *instantiates* a second filter, it never alters the math) ·
RL (ADR-0005) · LLM-decided moves (App E rule 25; book §6.5 mutual-consent exception not taken) ·
the police algorithm (sibling PRD) · core edits in this repo · genetic tuning runs (M5-4;
weight→config interface fixed in §4) · profiling computation (M5-5; consumes §3's ledger).

## 2. The DoD opponent and what "reference heuristic" means here

The M5-3 DoD: **≥60% arena win-rate (thief role) vs `ref-police`** — the reference cop heuristic
re-derived in core (police PRD §2): chase the belief argmax by Manhattan distance, wall the
step-cell at the reference's attributed `0.15` coin-flip when quota remains. Perception held
fixed: both sides read our `BeliefFilter` — so `ref-police` chases with a *sharper* belief than
the literal reference peer carries, the harder-opponent direction for our DoD (disclosed choice,
police PRD §2). Wins are survival outcomes over the seeded start-scenario suite (police PRD §4);
the committed table regenerates byte-identically from `config/arena.json`.

## 3. ThiefBrain algorithm (`copthief_thief.brain`)

**Move policy — region-survival (book §6.3.1 "your own heuristic algorithm" track):** score each
legal move by a config-weighted feature sum and take the max (one-ply with an adversarial threat
model — the cop is one mover; depth is spent on *area* analysis, not tree depth):

- **Worst-case distance** to the cop-belief's top-`search_top_k` support (each supposed cop cell
  answers with its best reply toward us — min over that, expectation over the support): richer
  than `ref-thief`'s argmax-only flight, and it is the *survival clock* feature — its weight
  ramps as `steps_survived → survival_threshold` (near the end, distance is everything).
- **Safe-region size:** belief-weighted count of cells we reach strictly before the cop can
  (two-front BFS from our candidate cell vs each supposed cop cell) — the region-survival core:
  prefer the move that keeps the largest territory ours.
- **Articulation awareness:** Tarjan articulation points over the open-cell grid graph; entering
  a component that (a) hangs behind an articulation point and (b) is sealable by the cop's
  *remaining barrier quota* — or is smaller than the remaining survival steps — is a trap and is
  penalized in proportion to how cheaply it closes. This is the direct counter to the sibling
  brain's barrier graph-surgery.
- **Spread bonus** for unvisited cells (the reference thief's one good instinct, attributed):
  fresh cells decorrelate our trail from our history and starve the scent likelihood.

**Deception timing — the M5-3 headline.** M3-4 built the lie mechanism (closed-vocabulary
gazetteer hints, `intent` sealed `truth`/`lie` per the reference constants, injection-safe
parsing); M5-3 decides *when*. Instrument: the **self-mirror** — a second `BeliefFilter`
instance, public API only, fed exactly the evidence *we* have transmitted (our smell grids, our
hints' implied cells). It estimates what a rational opponent can know about us — SQ3's
distrust-symmetric twin: they can fake evidence at us, we can *meter* what our honest physics
leaks. Policy, all thresholds from config: **lie** when the mirror is sharp on our true cell
(`P(truth) ≥ mirror_sharp_p`) *and* the cop-belief places the cop near (≤ `near_distance`) —
i.e. exactly when they know and can act; the lying hint names a gazetteer landmark implying cells
**away from our planned heading** (decoy = the region-survival runner-up direction, so the lie
covers the move we did *not* take). **Truth (or the neutral bank)** otherwise — credibility is a
budget: post-audit, opponents profile our lie-rate (as we do theirs, M5-5) and discount our
hints; `lie_budget` caps lies per mini-game and `lie_cooldown` spaces them. Intent is sealed
truthfully either way — the audit sees `lie` labels; the *wire* hint is the deception (App E-
compliant: lying in hints is legal play, lying in sealed state is forfeit). **M5-6 seam:** the
hint text comes from a template bank selected in `[strategy.thief]`; the A/B arena run measures
deception efficacy (opponent belief-error induced per lie — computable in referee mode where
truth is known) across banks and ships the winner.

**Determinism** given seed; perf trivially inside the config budget (Tarjan + BFS on ≤100 cells).

## 4. Configuration

All weights/thresholds in `game.toml [strategy.thief]` (private, never signed, never wire):
feature weights (`w_distance`, `w_region`, `w_articulation`, `w_spread`), survival-ramp shape,
`search_top_k`, deception knobs (`mirror_sharp_p`, `near_distance`, `lie_budget`,
`lie_cooldown`, template bank id). Loader defaults; zero literals in `src/` (constraint #5).
M5-4's GA tunes exactly this weight vector (fixed order, per-gene bounds — HW6 genome pattern,
attributed) offline in referee mode; the artifact + fitness curve commit here; tuned weights
never reach the sparring host. `[strategy] thief_class` selects the brain by the book §6.2
dotted notation (`copthief_thief.brain:ThiefBrain`); `config/arena.json` (this repo's copy)
lists this roster + the DoD threshold.

## 5. Process guards

Champion gate: this repo's pin (`greedy-manhattan` both roles) may fall to `ref-thief`,
`ref-police`, or `ThiefBrain` on the new per-role tables — any dethroning updates
`config/arena_champion.json` **in the same PR** with the regenerated table (CLAUDE.md §5). Core
arrives by sync only; if the M5 core groundwork and this brain land in the same window, the sync
PR merges **first**, then the brain PR rebases on it. No wire change: the thief sends no
barriers; hints/intent flow through the M3-4 path unchanged.

## 6. File & test layout (≤150-line files)

This repo only: `copthief_thief/brain.py` + `regions.py` (two-front BFS + component sizes) +
`articulation.py` (Tarjan) + `deception.py` (self-mirror + timing policy), split as size
demands; tests under `tests/role/thief/`. Mirrored suites keep exercising core with core brains;
the mirrored arena integration test reads this repo's `config/arena.json` roster.

## 7. Test plan (TDD; DoD of M5-3)

Unit: flees the certain cop · safe-region prefers the open side in a corridor fork ·
articulation penalty rejects a sealable pocket (and accepts it when the cop's quota is spent —
the same board, quota 0, flips the choice) · survival ramp dominates near threshold · self-mirror
sharpens on our true cell under our own honest trail · lie fires exactly in the
sharp-mirror × near-cop quadrant, respects budget/cooldown, decoys away from the actual heading,
seals `intent="lie"` · truth path leaves intent `truth` · determinism per seed. Property: chosen
move always legal; lie count ≤ budget; region scores non-negative. Integration (keyless CI,
config-driven): **the DoD series** — ThiefBrain vs `ref-police` over the committed scenario
suite, survival rate ≥ the configured 0.60, CI-blocking · deception-efficacy metric computes in
referee mode (feeds M5-6) · champion gate green on the updated pin. Full local gate ritual before
every push.

## 8. Acceptance criteria (binary)

- All §7 tests green in keyless CI (role suite here; core prerequisites already green post-sync).
- `docs/evidence/m5-arena-thief.md` committed: DoD table (ThiefBrain vs `ref-police`,
  per-scenario outcomes + rate) + regenerated per-role standings; script-generated only.
- `config/arena_champion.json` (this repo) consistent with the committed tables.
- Deception timing observably *conditional* in the evidence: the committed table splits belief-
  error induced per lie vs per truth-hint (the M5-6 baseline measurement).
- No LLM import in `copthief_thief` or the strategy path (AST-scan pin, mirroring the police
  repo's) — the verbal layer stays zero-token templates (App E rule 25, G4).
