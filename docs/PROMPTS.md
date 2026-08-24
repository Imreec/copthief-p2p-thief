# Prompt Engineering Log

> Truthful, per-PR entries for **committed** work only (CLAUDE.md §7). Development prompts —
> runtime agent prompts live in source. Format: PR · driver/reviewer · what was asked · outcome.

## PR (this one) — m8-structure-polish (README corrections, Imree's review round)

- **Driver:** Imree · **Author:** Claude (terminal) · **Reviewer:** PR left open for Imree's
  review — not self-merged.
- **Outcome:** point totals stated exactly (617:517 on the board, 677:547 with diversity —
  the en-dash form read like a range); the two lead-repo deep links updated to the
  per-opponent `reports/counted-series/` layout that lands with cop #156. The lead repo's
  half of this round (the reports-tree reorganization itself + its TODO truth pass) is cop
  #156; the mirrored chart-script change arrives here via the post-merge sync ritual.

## PR #107 — docs/m8-readme-report (M8-1 + M8-2 + sync; polish follow-up #108)

- **Driver:** Imree ("I want our readme to be a masterpiece... take the HW6 readme as the
  floor"; role deltas per repo) · **Author:** Claude (terminal) · **Reviewer:** cross-model
  review on the thread.
- **What was asked:** this repo's half of the M8-1 README pair — the full §9.4.2 academic
  report narrating THE THIEF, with real visual assets — plus KNOWN_LIMITATIONS.md and
  SELF_GRADE.md.
- **Outcome:** README rebuilt as the evader's report (Dec-POMDP with the belief used
  worst-case-first, thief-specific orchestration dilemmas — pacing under the survival clock,
  honest cage concession — the doctrine-evader stack with its measured numbers and the k=4
  trade stated plainly, ThiefBrain + the opponent lab with this repo's own evidence trail,
  GA/self-play curves, screenshots). Assets all real and regenerable: the counted vm__fabi
  g01 survival GIF from the committed audit log (log added to docs/evidence/), a live-GUI
  screenshot captured from a real local match in this repo (the M4-2 deferred item), a
  replay-GUI Verified-OK capture on the counted log, belief-vs-truth overlays, notebook
  figure extracts. KNOWN_LIMITATIONS.md carries the thief-side T-01…T-06 (the k=4 trade,
  lead-side evidence topology, the inert M5 tables, the modest GA delta, single committed
  wire log, offline-only deception evidence) + the lead's L-entries by reference.
  SELF_GRADE.md == `self_grade.py` output (93.0, config v1.01). pyproject gains the pillow
  viz dep + the `arena` marker/addopts (pairs with the lead's ADR-0018 CI slim, whose
  workflows/tests arrive via the sync ritual). TODO M8-1/M8-2 ticked; M4-2's deferred
  screenshot noted delivered.

## PR — chore/m8-todo-truth-pass (the TODO stops being a second journal)

- **Driver:** Imree (asked for a pre-M8 cleanup of the drift sources in both repos) ·
  **Author:** Claude (terminal) · **Reviewer:** pending (AG).
- **What was asked:** the same truth-pass as the cop repo's, applied to this copy. This copy was
  the staler one: M7-3 (first friendly), M7-6 (email posture, synced here as PR #35 on 2026-07-20)
  and M7-10 still showed ☐; M7-46/47/51 showed ◐ though merged (#72/#73); and standing rule S-5
  still carried the pre-ADR-0008 draft wording the cop repo corrected on 2026-07-20 — a
  standing-rule divergence between the two repos.
- **Outcome:** every status re-verified against `git log` (incl. the sync commits as the arrival
  record for cop-led milestones); ☑ entries compressed to status + pointers (dossiers remain in
  git history); dispositions on all open items mirror the cop TODO (M7-0/1/2/5/8 + the new M7-55
  pointer to the unmerged opponent-identity fix, cop-led); S-5 reworded to the ADR-0008 form with
  the divergence disclosed in-line. Header gains the entry-discipline rule.

## PR — m7-46-47-siege-and-informed-ramp (two opponents, two conditional responses)

- **Driver:** Imree · **Author:** Claude (terminal) · **Reviewer:** pending (AG).
- **What was asked:** improve the thief against uoh-sqak's cop, which took all three thief
  sub-games of the 2026-08-07 friendly with identical play; read their PUBLISHED source
  rather than infer; keep every existing arm at beat-or-tie; do not repeat M7-21's
  unmeasured weight change.
- **Outcome, M7-46:** their `ApexCop` was ported and **reproduces the friendly turn for
  turn, 14 of 14** — every barrier cell and every cop cell — which validated the port and,
  with it, three corrections. The loss was not our thief "camping": their depth-8 solver had
  PROVEN the capture two plies earlier. Their belief on us is EXACT every turn, so deception
  never reaches this cop. And the thing that actually decided it was **tempo** — their cop
  took a step AND a wall in the same turn, which chapter 3's Barrier Law does not grant.
  Under the book's turn law their policy captured nothing in 64 games. Shipped
  `features.support_width`: narrow the flight vector only once the opponent's wall RATE
  proves a siege. 0/32 → 10/32 at their live tempo, signed start flips to survival.
- **Outcome, M7-47:** gating M7-46 surfaced that best2934's cop — our OTHER counted
  opponent — was taking 14 of 32 off us, including the signed start. **First number reported
  was 23/32 and was wrong**: measured with the capture-claim channel off, the exact
  unmodelled-channel error `m7-45-best2934.md` already warns about. Cause: the base table's
  `ramp_start_fraction` 0.9496 arms the flight ramp at step 33 of 35, so it never fires.
- **The trap, recorded because the gate nearly missed it:** arming the ramp early
  unconditionally scores 32/32 against best2934 and collapses us **8/8 → 0/8** against a
  quiet chaser, DoD 84% → 62% — **and the regression gate still reported GREEN**, because
  the pin only fires when a challenger TOPS a champion. Our own brain regressing is
  invisible to it. On a thief change the per-arm rows are the evidence, never the verdict.
- **What shipped instead:** the ramp arms on the BELIEF (peak mass ≥ 0.9 — i.e. the cop
  declared its cell) on its own separate multiplier, so the GA-tuned clock ramp is untouched
  and a quiet cop leaves the brain bit-for-bit as tuned. Informed world 128/128,
  better-or-equal on every arm; CI arena byte-identical; M7-46 unmoved.
- **Named, not fixed:** `config/ga.json` bounds `ramp_start_fraction` to [0.3, 0.95] — every
  value that helps is below 0.3, so the GA could not have found this and did not. A null
  result from a search that cannot reach the answer is not a null result.
- **Rejected and kept as labelled negatives:** unconditional `top_k` 4 → 1 (wins vs uoh-sqak,
  regresses every existing arm) and a centrality term aimed at their solver's trigger
  (0/16 at every weight).

## PR #61 — m7-30-thief-vs-walling (the retune that did not work, and why it could not)

- **Driver:** Imree · **Author:** Claude (terminal) · **Reviewer:** pending (AG).
- **What was asked:** after the warm-up lost s1/s3/s5 to corner seals, retune the thief
  against walling cops — probe first, add a walling arm to the pool without replacing
  anything, and gate against the deployed M7-21 overlay on every arm.
- **Outcome:** **null result on the retune; a real defect found instead.** The probe was
  meant to size the headroom and instead overturned the premise: the gene the retune was
  supposed to raise, `w_articulation`, cannot be seen by the arena at all — referee mode
  builds the thief's Observation without the barrier quota, so its trap branch never fires,
  while the live peer path always fires it. Values a decade apart produce bit-identical
  games. The GA improved pool fitness 0.615 → 0.828 and still lost the gate, on the one arm
  the milestone was aimed at. Nothing deployed; `game.toml` untouched.
- **The uncomfortable part, stated rather than buried:** this means M7-21's own published
  headline — `w_articulation` "falling from the box ceiling 40.0 to 8.93" — was free drift
  the instrument could not score, and it changed how the agent plays for real. Our own prior
  evidence needed correcting, so it is corrected in the same document that found it.
- **Discipline note:** three temptations refused. (a) Tuning on the broken instrument
  anyway — it would have produced a shippable-looking vector measuring a fiction. (b)
  Re-rolling the GA after seeing the gate fail — the gate is not a training target, and a
  pool chosen to clear it would be exactly that. (c) Deploying on the aggregate (2220 v
  2200, better on three arms) — beat-or-tie means every arm, and the arm it lost is the
  quiet waller, the closest model of the cop that actually beat us.
- **Scope honesty:** the fix the finding calls for is in mirrored core, which this repo may
  not edit, so it is named as a police-lead follow-up rather than quietly worked around. The
  one deployment question that is thief-side (`w_articulation` → 0.0) is left undeployed and
  put to Imree, because its justification is instrument↔wire agreement rather than a
  measured win — and a gate that certifies a tie is not a mandate.
- **Disclosed limit:** the probe measurements behind §1(a)–(d) of the evidence ran in a
  scratchpad harness that patches core, so they are **not** reproducible from this tree.
  Said so in the document rather than presenting them as repo-backed.
- **At review (2026-08-02):** he verified the `referee_obs` / `brains.py` / `turns.py`
  citations first-hand in both repos, answered the overlay question **no** (deployed weights
  stay — the divergence closes by fixing the instrument, not by moving a weight the gate
  cannot score), claimed the core fix as **M7-31** police-side, and required the dated
  corrections to the M7-21 evidence and TODO entry before merge. Writing those found one
  more error — **mine**: I had said M7-21's gate "rested on three informative arms, not
  four", and its own generated tables show `random` was 32 v 32 as well, so it rested on
  **two**. Corrected in both documents.

## PR #54 — m7-21-thief-retune-informed (the retune that actually worked)

- **Driver:** Imree · **Author:** Claude (terminal) · **Reviewer:** pending (AG).
- **What was asked:** after the cop-side retune failed its gate, he asked why not try the
  thief one now. Right call — it is the same class of task but a healthier instrument.
- **Outcome:** **wins both gates and ships.** The discipline that made it work was applying
  the M7-20 lesson FIRST: measure whether the pool can resolve its candidates BEFORE
  spending a GA run. It could (spreads 0.25–0.56), and it showed the headroom outright — a
  probe vector at 1.000 survival where the deployed one sat at 0.656. Fitness 0.602 → 0.805,
  and the evolved vector explains itself: `w_articulation` falls from its box ceiling
  because anti-cornering machinery earns its keep for a BLIND evader and gets in the way of
  an informed one.
- **Correction made mid-run:** the reference gate initially compared two book-v1 vectors
  under reference physics, which could not answer "should the base table change too?". Added
  the actually-deployed base vector as a third arm; it ties the new one (950–950), so the
  base stays untouched and only the overlay moves.
- **Discipline note:** the GA pool deliberately mixes informed and uninformed worlds, and
  models the quiet cop conservatively (captures are not claim-gated, so it is treated as
  dangerous as a loud cop). A vector tuned against a fully-informed world would have looked
  better and been more fragile.

## PR #52 — sync-m7-18-claim-channel (the claim channel arrives, and pays here)

- **Driver:** Imree · **Author:** Claude (terminal) · **Reviewer:** pending (AG).
- **What was asked:** sync the M7-18 core from the police repo, then take the one
  measurement the lead repo could not — its configured thief is `random`, so the number
  for the vector we actually ship had to be taken here.
- **Outcome:** sync first, on the ritual (820 keyless tests green HERE before the sync was
  committed; mirrored tests confirmed role-blind; mirror verify 284). Then the measurement,
  and it is the answer M7-16's disclosed 8/32 warning was waiting for: peer-path exact
  cop-tracking 0.502 → 0.994, and the deployed vector's survivals against both chasers
  8 → 21 of 32, points 945 → 1115. The A/B is controlled — same brain, same options, only
  the feed differs — and its hidden column reproduces the committed M7-16 table
  cell-for-cell, which is the check that makes the delta trustworthy.
- **Discipline note:** no strategy weight changed; the gain is information, not tuning. Two
  follow-ups are named rather than folded in (this repo's GA pool tuned the vector under a
  HIDDEN feed and may now be the wrong shape; the cop's pool understates a real
  claim-reader), because both change deployed weights and deserve their own evidence.

## PR #50 — feat/m7-16-thief-bookv1-retune (anti-camping from selection ⚑)

- **Driver:** Imree · **Author:** Claude (terminal) · **Reviewer:** pending (AG).
- **What was asked:** the sibling half of the counted-series strategy prep, queued
  behind the M7-15 sync by Imree's "close the open items" instruction.
- **What landed:** `config/ga_bookv1.json` (mixed pool of four belief-cop worlds
  under the pair-locked physics), the retune artifact (survival 0.391 → 0.609; the
  headline is `ramp_start_fraction` crashing from 0.95 to the 0.3 box floor — the
  camping habit the postmortem flagged, priced out by selection), the two gate
  arenas (new wins book-v1, old keeps reference — physics-specific, same as the
  cop side), deployment on the `[strategy.thief.multiplicative_book_v1]` overlay
  with the base untouched, and the evidence doc. Non-mirrored changes only
  (config + docs); the machinery arrived via sync #49.
- **Honesty notes:** the cop pool is core-name heuristics bracketing a threat
  class, not the opponent's build; book-v1 stays cop-favored at these arms and the
  doc says so.

## PR #26 — feat/m5-7-thief-notebook (M5-7 results notebook, executed + pinned ⚑)

- **Driver:** Imree (session brief: M5-7 notebook — arena + GA curves + sensitivity;
  LaTeX + citations; committed with outputs) · **Author:** Claude (terminal) ·
  **Reviewer:** Antigravity + Eyal (per TODO); stacked on PR #25 (the notebook renders
  its A/B evidence).
- **This PR:** sync delta from cop@8daa5ff (the mirrored renders-clean pin
  `tests/integration/test_notebook.py` — it rides HERE, not the sync PR, because it
  needs this repo's notebook to exist) + `notebook` dep group parity + the executed
  `notebooks/results_analysis.ipynb`: metric identities in LaTeX + citations (book
  ch.6/§6.3.1, ADR-0002/0005, PRD §§) · arena standings + champion gate GREEN · DoD
  27/32 = 84% PASS live-computed with the deployed evolved weights · GA curve
  0.708→0.792 with default baseline · w_distance/ramp_start_fraction sensitivity
  sweeps · the M5-6 A/B table rendered verbatim from the committed evidence.
  TODO M5-7 ticked. **Phase M5 complete in both repos once this chain merges.**

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
