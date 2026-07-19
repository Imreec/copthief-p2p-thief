# Prompt Engineering Log

> Truthful, per-PR entries for **committed** work only (CLAUDE.md §7). Development prompts —
> runtime agent prompts live in source. Format: PR · driver/reviewer · what was asked · outcome.

## PR #25 — feat/m5-6-thief-ab (M5-6 template-bank A/B — measured, winner shipped ⚑)

- **Driver:** Imree (session brief: "M5-6 template-bank A/B — deception efficacy metric
  in referee mode; winning bank shipped") · **Author:** Claude (terminal) · **Reviewer:**
  Antigravity (cross-model); stacked on PR #24; core instrument from cop PR #39.
- **This PR:** `config/deception_ab.json` (banks classic+terse · ref-police at the
  attributed 0.15 · ThiefBrain with the DEPLOYED evolved weights · fresh seeds 501–532,
  disjoint from DoD/GA/holdout) → committed `docs/evidence/m5-template-ab.md` →
  **winner `classic` shipped** in `[strategy] hint_bank`. Candid findings, both
  disclosed in the evidence: (1) banks measure IDENTICAL — wording is neutral to our
  own closed-vocabulary parser by construction; (2) lie efficacy is real but tiny
  (+0.000042 error/lie vs −0.006730 per truth-hint): the timing policy lies exactly
  when the exact-Bayes tracker is already near-certain, where decoy mass barely moves —
  a strategy-track observation for the report. A first 4dp table rounded the lie delta
  to +0.0000; the instrument was fixed to 6dp (cop-side script, synced) BEFORE
  committing evidence — numbers must not round the result away. TODO M5-6 ticked.

## PR #24 — feat/m5-thief-clock-anchors (signed-clock anchors + thief GA run, M5-4 ⚑)

- **Driver:** Imree (delegated decisions: signed-clock anchors + thief GA; merge nothing) ·
  **Author:** Claude (terminal) · **Reviewer:** Antigravity (cross-model); stacked on
  sync PR #23.
- **This PR:** RED anchor pins → GREEN `survival_ramp` (ramp_start_fraction × the
  SIGNED threshold; 0.7×35 = the old step-25 behavior byte-for-byte — committed arena
  table regenerates identically) + `trap_ceiling` (fraction of the capped REMAINING
  clock; pockets that outlast the clock open up late game — pinned both ways). The
  PRD §3 deviation note retired; gene box follows. **GA run honesty:** the first
  16-seed run plateaued flat (0.688 = best random candidate, curve FLAT); widened the
  instrument on training signal only — 32 seeds improved but validated as an off-suite
  wash (51/64 vs default 52/64, NOT deployed); the committed 48-seed × pop-16 × 16-gen
  run improved 0.708→0.792 and validated off-suite: **DoD 78%→84% (breaks the M5-3
  greedy tie), holdout 84%→81%, net across suites 91/112 vs 86/112 — deployed** to
  `arena.json` brain_options + `[strategy.thief]`. Champion pin honestly stays
  `greedy-manhattan` (the 8-seed round-robin still ties; a tie is not a dethroning).
  TODO M5-4 ticked.

## PR #23 — sync/m5-core-post-36 (post-#35/#36 core sync + GA parity)

- **Driver:** Imree (session directive: build the chain, merge nothing; sync + thief GA
  delegated) · **Author:** Claude (terminal) · **Reviewer:** Antigravity (cross-model).
- **This PR:** the sync ritual covering the mirror lag left by design last session —
  cop #35 (M5-4 genetic core: `strategy/genetic/`, `scripts/ga_run.py`, GA smoke suite,
  session/facade M1-walk pins) + cop #36 (Observation signed clock: `survival_threshold`
  + `max_moves` at the referee and peer seams), synced from the cop branch tree
  @af400a5 (content-hashed mirror, the #21 precedent). Parity: this repo's own
  `config/ga.json` — ThiefBrain continuous-weight gene box vs `ref-police` (the mirrored
  GA suite loads it at module level; role-blind per the PR #29 rule). Gotcha-#9 audit:
  full thief suite run BEFORE the sync commit — 406 passed; all gates green.

## PR #22 — feat/m5-3-thief-brain (M5-3 — ThiefBrain, the graded core ⚑)

- **Driver:** Imree ("continue and build what you need for M5; merge nothing tonight" —
  AFK directive) · **Author:** Claude (terminal) · **Reviewer:** Antigravity
  (cross-model, on the PR); merge order: after sync PR #21.
- **This PR (stacked on sync/m5-core):** RED `tests/role/` pins → GREEN `copthief_thief`
  (never mirrored): region-survival scoring (worst-case distance vs top-k cop belief with
  survival-clock ramp · two-front-BFS safe region · Tarjan articulation trap-awareness
  gated on the cop's REMAINING quota — the pocket flip is pinned both ways · unvisited
  spread) + deception timing (self-mirror = second BeliefFilter over OUR OWN transmitted
  evidence, public API only — M3-8 boundary intact; lie iff mirror-sharp AND cop-near;
  decoy = farthest landmark from the actual heading; budget+cooldown; intent sealed
  truthfully through the M5-3 hint-intent seam). Knobs in `features.DEFAULT_OPTIONS`
  (AppFTable pattern) + `[strategy.thief]`/arena overrides (the M5-4 GA interface);
  `top_k=4` default chosen on DoD 25/32=78% + holdout 23/32=72%. **DoD observed and
  CI-blocking: 78% survival vs `ref-police` (floor 60%).** Candid: greedy-manhattan ties
  25/32 vs ref-police on this suite — the champion pin honestly stays greedy (tie is not
  a dethroning); the brain's trap machinery targets barrier-surgery cops, unmeasurable
  cross-repo by design. Guards: App-E-25 AST scan, legality property, perf ceiling.
  TODO M5-3 ticked in the same change.

## PR #20 — docs/m5-1-thief-brain-prd (M5-1 gate — ThiefBrain PRD)

- **Driver:** Imree (M5 session brief in the police repo: role-split + reference-heuristic
  questions posed as PRD inputs; M3-8 scent internals fenced off) · **Author:** Claude
  (terminal) · **Reviewer:** Imree (docs gate — merge = the approval, together with police
  PR #30).
- **Context:** shared recon logged in the police repo's PROMPTS entry (PR #30) — book ch.6,
  reference brains @960499fd, SQ2/SQ3, sync topology. Thief-specific groundwork: the M3-4 lie
  mechanism (gazetteer + sealed intent) deliberately shipped without a timing policy — this PRD
  supplies it; the self-mirror instrument (second BeliefFilter over our own emitted evidence,
  public API only) keeps the M3-8 boundary intact.
- **This PR:** `docs/PRD_thief_brain.md` — role split (ThiefBrain in `copthief_thief`, core by
  sync only) · DoD ≥60% survival vs the re-derived `ref-police` over the seeded scenario suite ·
  region-survival scoring (worst-case distance + survival ramp, two-front-BFS safe region,
  Tarjan articulation trap-awareness vs remaining barrier quota, unvisited spread) · deception
  timing (lie iff mirror-sharp AND cop-near; decoy away from actual heading; budget/cooldown;
  intent sealed truthfully) · M5-6 template-bank seam + efficacy metric · all knobs in
  `[strategy.thief]`. TODO M5-1 ticked in the same change (true at merge).

## PR #9 — sync/m1-8-logger (M1-8 arrival — phase M1 complete)

- **Driver:** Imree (authorized the lead merge + the final M1 sync) · **Author:** Claude
  (terminal) · **Reviewer:** cross-model review ran on the police PR (copthief-p2p-cop#10);
  mechanical landing.
- **This PR:** `sync: core from police@5823d5b` — JSONL logger, match-runner instrumentation,
  replay-from-log (tamper + hint-divergence detection runs in THIS repo's CI too), CLI --log.
  TODO M1-8 ticked. **Phase M1 complete in both repos: M1-1..M1-8 all ☑.**

## PR #8 — sync/m1-7-sdk (M1-7 arrival + pyproject parity)

- **Driver:** Imree (authorized the lead merge + "continue") · **Author:** Claude (terminal) ·
  **Reviewer:** cross-model review ran on the police PR (copthief-p2p-cop#9); mechanical landing.
- **This PR:** `sync: core from police@6146bbc` — SDK facade, `copthief` CLI, real FastMCP
  adapters, p2p driver, evidence-backed live test. Plus manual pyproject parity (NOT mirrored):
  `fastmcp>=3.4.4` dependency + lockfile, `[project.scripts] copthief`, live-adapter coverage
  omits. TODO M1-6/M1-7 ticked (M1 exit observed on the lead; evidence committed there).

## PR #7 — sync/m1-5-6-core (M1-5 + M1-6 arrival)

- **Driver:** Imree (authorized the lead merges + "continue") · **Author:** Claude (terminal) ·
  **Reviewer:** cross-model review ran on the police PRs (copthief-p2p-cop#7, #8); mechanical
  landing. (The first M1-5 sync attempt, PR #6 here, was closed red: tests/unit/wire had missed
  the lead's explicit MIRRORED list; the lead now mirrors whole test trees.)
- **This PR:** role test moved to tests/role/ (per-repo, outside the mirror), then
  `sync: core from police@2f6f441` — the wire layer (M1-5) and the peer loop + in-process MCP
  fake (M1-6 fake-transport half: full mini-game with mutual audit runs in THIS repo's CI too).
  TODO M1-5 ticked, M1-6 marked ◐ (one-command two-process form rides with M1-7).

## PR #5 — sync/m1-4-state-machine (M1-4 arrival)

- **Driver:** Imree (authorized the lead merge + "continue") · **Author:** Claude (terminal) ·
  **Reviewer:** cross-model review ran on the police PR (copthief-p2p-cop#6); mechanical landing.
- **This PR:** `sync: core from police@7dc7e48` — the game state machine (frozen PLAN §5 table)
  and its 49-pair exhaustive test suite. TODO M1-4 ticked.

## PR #4 — sync/m1-core (M1-2 + M1-3 arrival)

- **Driver:** Imree (authorized the lead merges + "continue") · **Author:** Claude (terminal) ·
  **Reviewer:** cross-model review ran on the police PRs (copthief-p2p-cop#4, #5); this PR is
  their mechanical, hash-verified landing.
- **This PR:** `sync: core from police@3e747bf` — M1-2 (board/rules/scoring, App F guard, typed
  loader) + M1-3 (crypto from kit CORE, terms extraction, conformance fixtures) + the core test
  tree (now MIRRORED). Plus this repo's config tree: game.json / app_f_table.json /
  rate_limits.json identical to the lead, game.toml role-adapted (thief identity, port 8801).
  All gates green here: 73 tests, 100% coverage, kit CORE vectors green (M1-3 DoD "both repos"
  satisfied). TODO M1-2/M1-3 ticked.

## PR #3 — docs/m1-mechanism-prds (M1-1 gate, thief-side landing)

- **Driver:** Imree (approved both PRDs at the M1-1 gate in the police repo) · **Author:** Claude
  (terminal) · **Reviewer:** cross-model review ran on the police PR
  (Imreec/copthief-p2p-cop#3); this landing copies the merged text.
- **This PR:** `docs/PRD_engine.md` + `docs/PRD_crypto.md` copied from the police (lead) repo
  with a this-copy role note added — engine/crypto are role-agnostic core mechanisms (ADR-0001
  docs convention: docs land per-repo, code arrives via sync). TODO M1-1 ticked.

## PR #1 — chore/m0-bootstrap (M0 process bedrock)

- **Driver:** Imree (direction, approvals, repo/remote setup) · **Author:** Claude (terminal) ·
  **Reviewer:** Antigravity (cross-model) + Eyal.
- **Context:** Phase 0 (book v3.0.0 absorbed: clarification page, App C/D/E/F, ch.2/3/4/5/6/7/8/9;
  kit verified; reference repo studied; rubric V3 diffed vs HW6) → Phase 1 decision grill
  (topics a–h + creativity round, each decision argued and approved one-by-one) → Phase 2 gated
  docs (PRD v2, PLAN, TODO, CLAUDE.md + ports plan — each explicitly approved by Imree; PRD/PLAN
  cross-model-reviewed pre-repo, findings adjudicated with sources).
- **This PR:** repo scaffolding (uv/pyproject/quality config), CI workflow + six gate scripts
  (file sizes, anti-patterns, no-hardcoded, sync-core manifest, self-grade validation, submission
  checklist), five adapted skills (eval-harness + self-grade rewritten for this project's
  inversions; HW6's "pipeline not strategy" and "repo is public" lines deliberately removed),
  approved PRD/PLAN/TODO/CLAUDE.md landed, ADR-0001/0002, process templates, package skeletons +
  version tests. Everything adapted from HW6 was audited line-by-line per the porting rule —
  nothing blind-copied.
