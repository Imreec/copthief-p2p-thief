# TODO — Cops-and-Robbers P2P Race

> **Status: APPROVED (Phase 2 gate, 2026-07-16).** **This copy: the thief repo (role package `copthief_thief`).**
> Living document: checkboxes tick as work
> **lands on `main`**, never as aspiration. Statuses: ☐ not started · ◐ in progress · ☑ done.
> Owner key: **I** = Imree (drives, approves, operates sends/arming) · **C** = Claude (authors
> code/docs under I's direction) · **E** = Eyal (reviews, per-task ownership) · **AG** =
> Antigravity (cross-model PR review). Every task's DoD includes: CI green, ≤150-line files,
> tests per TDD, reviewed PR. ⚑ = role-repo-specific task.

## Phase M0 — Process bedrock *(gate: PRD/PLAN/TODO approved in repo form)*

- ☑ **M0-1** Scaffold both repos (uv, pyproject, ruff/mypy/coverage config, empty `src/` layout per PLAN §3) — I+C. DoD: CI green on empty src in both.
- ☑ **M0-2** Port + adapt CI workflows from HW6 (keyless gates: ruff, mypy --strict, pytest+coverage fail_under, 150-line check, no-hardcoded scan, secret scan) — C, review E. DoD: each gate demonstrably fails on a seeded violation. (M0 record: anti-pattern + mirror gates fired on real violations; remaining gates' negative tests ride with the M1 suite.)
- ☑ **M0-3** `scripts/sync_core.py` + `sync_manifest.json` + CI manifest gate — C, review AG. DoD: PLAN §13 M0 drift test observed (induced drift → sibling CI red).
- ☑ **M0-4** CLAUDE.md ×2 (HW6-derived, rubric-V3 diff applied, kit-conformance clause) — C, approve I. DoD: I approved both files.
- ☑ **M0-5** Port `.claude/skills/` (commit-discipline, pr-discipline, tdd-cycle, self-grade, eval-harness→arena-harness rewording) + `docs/REVIEW_PROCESS.md` — C. DoD: skills reference this project, not HW6.
- ☑ **M0-6** Land approved PRD/PLAN/TODO as `docs/` in both repos (⚑ role deltas applied) — C, approve I. DoD: docs match approved drafts + amendments.
- ☑ **M0-7** `docs/adr/0001-sync-mirror.md` + `0002-reference-reuse.md` — C. DoD: ADR format per PLAN §14.
- ☑ **M0-8** `scripts/check_submission.py` skeleton (App C table 6 + guidelines §17 checklist, red until items land) — C. DoD: runs in CI as non-blocking report.

## Phase M1 — Walking skeleton *(PRD_engine + PRD_crypto precede code)*

- ☑ **M1-1** `docs/PRD_engine.md` + `docs/PRD_crypto.md` (mechanism PRDs) — C, approve I.
- ☑ **M1-2** `domain/board+rules+scoring` (config-driven, App F guard in `shared/config`) — C, review E/AG. DoD: unit tests incl. capture-by-barrier, imprisonment, tie rule; ≥90% cov.
- ☑ **M1-3** `domain/crypto` from kit CORE (canonical, commit, terms sig, game_uid) + kit vectors as CI fixtures — C. DoD: all CORE vectors green in both repos.
- ☑ **M1-4** `domain/state machine` (transition table per PLAN §5) — C. DoD: property tests reject all illegal transitions.
- ☑ **M1-5** `wire/` dataclasses + validation (mirror reference fields; forward-compat rule) — C. DoD: schema tests incl. reject-missing/tolerate-unknown.
- ☑ **M1-6** `infra/mcp` server (4 tools) + client + in-process fake; `peer/` minimal loop (handshake→turns→audit, geometric play, template hints stubbed) — C, review AG. DoD: PLAN §13 M1 — one command, full localhost mini-game, self-audit pass. *(Observed on the lead repo 2026-07-17; evidence in its `docs/evidence/m1-p2p-match.md`.)*
- ☑ **M1-7** `sdk/` facade + CLI entry (`run peer`, `run local-match`) — C. DoD: all M1 flows callable only via sdk.
- ☑ **M1-8** JSONL logger (verbatim bytes, transitions, decisions, provenance) — C. DoD: M1 game replayable from log.

## Phase M2 — 🚦 Oracle spike (go/no-go gate)

- ☑ **M2-1** Reference peer run as oracle (sha 960499fd, keyless); Cloudflare named tunnel `copthief` on `imreeyal.com`, both hostnames (OI-3 decided) — I+C. DoD observed 2026-07-18: reachability both directions through the public edge. *(Executed from the police repo — lead evidence + ADRs live there; our thief peer played pairing 2.)*
- ☑ **M2-2** Both role pairings vs the live reference over public URLs: mutual audit Verified OK both directions; our thief answered 35 straight capture claims (SQ2 live); shared game_uid verified cross-implementation — I+C. DoD: police repo `docs/evidence/` (spike notes §6 + four JSONL logs).
- ☑ **M2-3** SQ1/SQ2/SQ3 answered in writing against the running reference (police repo spike notes §3/§6) — C.
- ☑ **M2-4** `docs/adr/0003-crypto-early.md` + `0006-deploy-tunnel.md` (police repo, lead for shared ADRs) — C.
- ☑ **M2-5** **GO/NO-GO review with I** — **GO, 2026-07-18** (recorded in the police repo's spike notes §7–§8 with the residual-gap disclosure) — I.

## Phase M3 — Perception + arena

- ☑ **M3-1** `docs/PRD_scent.md` + `docs/PRD_belief.md` (SQ1-informed) — C, approved I (police repo PR #16, 2026-07-18; PRDs live in the lead repo).
- ☑ **M3-2** `domain/scent` (kit-pinned form; locked-model doc w/ numeric example; ADR-0004) — C. DoD: kit pheromone vectors + decay/emission tests green.
- ☑ **M3-3** `domain/belief` exact Bayes filter (motion×scent×hint) — C, review E. DoD: beats last-known-position tracker on belief-error in referee sims (PLAN §13 M3).
- ☑ **M3-4** Gazetteer + hint templates (map_area landmarks; ≤hint_max_words; intent flag wired to sealing) — C. DoD: our hints round-trip our parser; injection-safety tests (hostile hint corpus).
- ☑ **M3-5** Baseline brains (random, greedy-Manhattan) via BrainBase seam — C. DoD: full headless series in referee + peer modes.
- ☑ **M3-6** Arena harness (sdk consumer; seeded round-robin; tables; champion regression gate in CI) — C, review E. DoD: seeded reproducibility test; gate red on champion loss.
- ☑ **M3-7** 🚦 **ADR-0004 revision decision — DECIDED: REVISE** (I, 2026-07-18, on C's seam assessment; league coordination `notes/LEAGUE-COORDINATION-ALON.md`). Add a second named scent model `multiplicative_book_v1` beside `subtractive_chebyshev_v1`, pair-locked via the locked-model doc + refusal rule, belief observation model parameterized. Assessment record: the cadence seam is two isolated decay calls in `peer/turns`; per-field decay count is once per FULL turn in reference and ours alike (the "half-turn" framing was imprecise — the real deltas are anchor/order/receiver-side convention); the locked-model doc is hashed+logged but NOT terms-signed (can't be, reference-frozen key set) — the build adds step-0 sealing of the model hash to close that.
- ☐ **M3-8** Named scent models — build (post-M4 or when inputs arrive; NOT inside M4) — C, approve I at the PRD gate. **UNBLOCKED — Alon inputs complete (2026-07-18/19, `notes/LEAGUE-COORDINATION-ALON.md`), spec facts for the PRD amendment:** kernel = book fig.4 **verbatim 5×5 lookup** (no closed form — discrepancy resolved: nobody fit a formula); cadence = ONE formula per FULL turn after both act, `τ′ = clamp((1−ρ)·τ + Δτ_kernel, 0, center_intensity)`; **EMPTY start**, end-of-turn anchor, NO receiver-side convention (each side recomputes, never receives); **NO rounding** in book-v3 (the reference rounds 3dp — a per-model numeric divergence to encode); ρ/center/kernel-size from signed config, kernel matrix a code constant mirrored in the lock doc; their 3-turn trace re-verified by us incl. the clamp case. **PREREQUISITE: kit-published locked-model DOC SCHEMA** — their bare `scent_model_sha256` (SHA256 over compact-canonical spec dict) and our structured doc are not comparable artifacts until the kit pins the exact bytes; the same schema also carries the wire-shape lock (M7-0). Then `docs/PRD_scent.md` amendment (settle `min_center_intensity` book-vs-reference provenance there) + `ADR-0004 v2` (approve-before-build), kit `multiplicative_book_v1` vectors as PROPOSED (promote when both implementations reproduce; founding fixtures = Alon's trace + kernel + clamp example, credited), ScentModel object refactor + cadence policy + belief parameterization + handshake refusal rule (refuse only when BOTH declare) + step-0 model-hash sealing + per-model belief-eval rerun. ⚑ Core build lands police-side and rides the sync.

## Phase M4 — Observability

- ☑ **M4-1** `docs/PRD_gui_replay.md` — C, approved I (police repo PR #24; PRD lives in the lead repo).
- ☑ **M4-2** Live GUI (heatmap + turn banner; local truth only) — C (police PRs #25/#26 + dark-theme facelift, core synced). DoD observed lead-side: `assets/m4-live-heatmap.png` from the real audited game `m4-local-g1` (police `docs/evidence/m4-observability.md`); ⚑ thief-window screenshot for THIS repo's README rides M8-1.
- ☑ **M4-3** Replay verifier (Verified OK / TAMPERED) — C, review AG (police PR #27, core synced; `copthief replay` works identically here). DoD observed lead-side: M2 g1 + M3 logs → Verified OK; mutated copy → TAMPERED exit 1; rule-19 mutation matrix runs in THIS repo's CI too (synced tests).
- ☑ **M4-4** Belief-vs-truth overlay + belief-error curve export — C (police PR #28, core synced). DoD observed lead-side: overlay + curve PNGs rendered from the real audited game via `copthief overlay`.

## Phase M5 — Intelligence ⚑

- ☑ **M5-1** ⚑ `docs/PRD_police_brain.md` (police repo) / `docs/PRD_thief_brain.md` (thief repo) — C, approved I (thief PR #20 + police PR #30, approved together; merge = the approval; ADR-0005 rides the police PR).
- ☐ **M5-2** ⚑ PoliceBrain: expectimax over belief + barrier graph-surgery + claim policy — C, review E. DoD: ≥60% arena vs reference heuristic (cop role).
- ☑ **M5-3** ⚑ ThiefBrain: region-survival + articulation awareness + deception timing — C, review E/AG (sync PR #21 + role PR #22). DoD OBSERVED, CI-blocking: 25/32 = **78%** survival vs `ref-police` over the 32-scenario suite (floor 60%; holdout seeds 101-132: 72%; `docs/evidence/m5-arena.md`). Candid note: the greedy baseline ties 25/32 vs ref-police on this suite — the brain's articulation/trap machinery targets barrier-surgery cops (the sibling PoliceBrain), unmeasurable cross-repo by design; further tuning = M5-4 GA. Deception timing unit-pinned (self-mirror quadrant, budget/cooldown, decoy-away-from-heading); efficacy metric = M5-6.
- ☑ **M5-4** Genetic tuning runs (HW6 salvage adapted; weights → config) — C. DoD OBSERVED: improving fitness curve committed (`docs/evidence/m5-ga.md`, 0.729→0.771 best over 16 generations × 48 fresh scenario seeds, default 0.708 → evolved 0.792; `config/ga_weights.json` artifact). Evolved thief weights validated OFF-suite (DoD 78%→**84%**, breaking the M5-3 greedy tie; holdout 401-432: 84%→81% — net positive across suites 91/112 vs 86/112, candidly disclosed) and deployed as config (`arena.json` brain_options + `game.toml [strategy.thief]`). Knobs anchored to the signed clock in the same PR (ramp_start_fraction × threshold; trap ceiling vs remaining steps — cop #36 Observation field).
- ☐ **M5-5** Post-audit opponent profiling (lie-rate, motion priors → next mini-game) — C. DoD: PLAN §13 M5 prior-shift test.
- ☑ **M5-6** Template-bank A/B in arena (deception efficacy metric) — C. DoD OBSERVED: measured table committed (`docs/evidence/m5-template-ab.md`, regenerable via `scripts/deception_ab.py`; renders in the M5-7 notebook); **winner `classic` shipped** in `game.toml [strategy] hint_bank`. Candid findings: banks measure IDENTICAL against our closed-vocabulary parser (wording-neutral by construction — differences would need cap-truncation or a different decoy policy); lie efficacy is real but tiny (+0.000042 error/lie vs −0.006730 per truth-hint) because the timing policy lies exactly when the exact-Bayes tracker is already near-certain — recorded as a strategy-track observation for the report.
- ☑ **M5-7** `notebooks/results_analysis.ipynb` (arena + sensitivity + curves; LaTeX + citations) — C, review E (PR #26). DoD OBSERVED: executed notebook committed WITH outputs (arena standings + champion gate GREEN · DoD 27/32 = 84% PASS · GA curve 0.708→0.792 · w_distance/ramp_start_fraction sensitivity sweeps as rendered PNGs · the M5-6 A/B table rendered from the committed evidence); renders-clean pin permanent CI (`tests/integration/test_notebook.py`, mirrored — execution counts, zero error outputs, figures present).

## Phase M6 — Reporting & fairness rail

- ☑ **M6-1** `docs/PRD_reporting.md` + `docs/PRD_gatekeeper.md` — C, approved I (cop PR #43; merge = the approval; D-decisions ruled on the PR thread — D1=A gmail.compose, dedicated team Gmail account; PRDs live in the cop repo, ⚑ lead).
- ☑ **M6-2** Four artifact schemas + writers (game_uid naming; canonical bytes = emailed bytes) — C, review AG (cop PR #44, arrives via this sync). DoD OBSERVED in the mirrored conformance battery (sample-run hashes recompute; files reproduce byte-for-byte). ⚠ Consensus signature (settlement-critical; credit Alon, verified vs reference `report_writer.py` @960499fd lines 22-25/81): SHA256 over `json.dumps(data, sort_keys=True, ensure_ascii=False)` with **DEFAULT (spaced) separators** — a third canonical variant, NOT our compact form — computed over the report **BEFORE** the `חתימת_קונסנזוס_משותפת` key is inserted (sign-then-insert); report schema is Hebrew-keyed per book §8.
- ☑ **M6-3** Step-0 declaration builder (hardware, model, tokens, commit hash, game-count) + signing — C (cop PR #45, arrives via this sync). DoD OBSERVED: real-HEAD pin runs per-repo (this checkout's own HEAD); sealed token fields + rule-19 matrix extension mirrored. Per-step token counts (`tokens_step`/`tokens_total`) go **INSIDE the sealed record** (`peer/sealing`) — the reference's own sealed schema does this (SQ3 list; league coordination re-confirmed).
- ◐ **M6-4** Gmail sender (compose-scope OAuth per D1=A; HW6 flow) + **draft default + arming interlock** — C, operate I (cop PR #47, arrives via this sync; parity here: `[email]` toml + CLAUDE.md §4 + `email-live` group + mypy override + `.env-example`). REMAINING for ☑: the live Gmail-draft evidence (OI-5 team account + consent; rides the M6-6 evidence run, ⚑ cop-led).
- ☑ **M6-5** Gatekeeper (quota → token bucket → DoS lock; `rate_limits.json` ≥ signed minimums asserted) — C (cop PR #46, arrives via this sync; + this repo's rate_limits.json v1.01 parity). DoD OBSERVED in the mirrored suite: synthetic load queues never crashes; 429 backoff schedule pinned; breaker trip/cooldown/reset.
- ☑ **M6-6** Series runner (`num_games`, per-game config commit, roles) — C (cop PR #48, arrives via this sync). DoD OBSERVED in the mirrored suite: 2-game local series → artifacts validate, roles alternate (F2), sealed game-count truthful, per-game logs replay Verified OK, M5-5 trust carry wired, email resting state refuses.
- ☑ **M6-7** Chaos drill harness (PLAN §10 drills) **+ watchdog/persistence (FR-8) + the FR-11 scent-physics audit check (D2-approved rider)** — C, review E (cop PR #50, arrives via this sync). DoD OBSERVED: the 10-drill battery is mirrored permanent CI; evidence doc ⚑ cop-side (`docs/evidence/m6-chaos.md` there).
- ☑ **M6-8** COST.md + token accounting on every LLM path — C (cop PR #49 + this repo's COST.md parity, this sync). DoD OBSERVED: mirrored `test_zero_tokens.py` pin (sealed 0/0 on a real audited game + Verified OK replay — cryptographically auditable).

## Phase M7 — League ops *(nothing announced unless true of the tree)*

- ☐ **M7-0** 🚦 **Wire-shape mutual ADR (joint with Alon/Renat) — PRE-SERIES BLOCKER for any counted game vs their team** — C drafts, I approves; co-signed by both teams; nothing posts/sends/co-signs without I's word. Position (citations book-verified 2026-07-19): `reference-v3` **resolves** the book's Ω_i self-contradiction (ch.1 §1.3: "no agent sees its rival" — rival position formally excluded from the observation space; ch.5's Reveal **deferred to the audit boundary, not skipped**); App D §4 precedence ("where the repo deviates, the book prevails") demotes demo interop to **corroboration** — ⚑ the one pair offered for Alon-team independent verification is THIS repo's `docs/evidence/m3-full-pairing-g1.jsonl` (+ `game.json` @ `16d526f`), staged with the reference-v3-physics caveat in `notes/outbox-alon-verification/`; `bookletter-v3` = registered **documented deviation** a pair locks by explicit sign-off (kit issue #6 disposition: register both shapes, asymmetric status); the wire-shape lock rides the SAME handshake locked-model doc schema as the scent models (M3-8 prerequisite, pinned once). Balance evidence committed cop-side: `docs/evidence/wire-shape-balance.md` (cop PR #41) — **common knowledge favors the EVADER** (aggregate cop 45.8%→26.6%; police-brain vs evading thieves 31/32 & 30/32 → 0/32), so "who adapts" is a competitive term, not a convenience. Drafts staged: `notes/DRAFT-ADR-WIRE-SHAPE.md`, `notes/DRAFT-REPLY-ALON-R2.md`, `notes/DRAFT-ISSUE6-DISPOSITION.md`.
- ☐ **M7-1** Sparring host deployed (both roles, generic brain, draft-pinned; OI-4 decided) — I+C. DoD: external reachability check passes 24h. IF the M3-7 ADR-0004 revision is approved: sparring peers accept either named scent model at negotiation.
- ☐ **M7-2** Kit: wire-contract page + JSON-schema fixtures + audit fixture (incl. tampered record) + **pre-match checklist & netcheck script** + SPEC §4 `_g<NN>` naming clarification — C, review E. DoD: kit CI green; I merges. League-coordination additions, each **"verify present, else add"** (an earlier kit PR from the planning session may land some first): `report_consensus_signature` vector (spaced form + sign-then-insert; **credit Alon by name**) · F-421 Host-header deployment note (posted as kit issue #4) · named scent-model vectors (M3-7-gated) · **locked-model DOC-SCHEMA pin** (one schema serving scent models AND wire shapes; M3-8/M7-0 prerequisite) · named wire-shape registrations per the issue-#6 disposition (M7-0-gated; `bookletter-v3` fixtures = Alon's team's contribution, credited, PROPOSED until independently reproduced).
- ☐ **M7-3** League outreach round (Alon first) + demo friendlies; cross-audit clean — I (all sends I-authorized). DoD: ≥1 external friendly, clean mutual audit, notes filed.
- ☐ **M7-4** First counted series (armed by I; full interlock path) — I. DoD: both reports accepted; artifacts + config committed; profiling notes stored.
- ☐ **M7-5** Additional counted series vs distinct teams as roster allows (target: all reachable) — I. DoD: per-series artifacts committed.

## Phase M8 — Submission hardening

- ☐ **M8-1** README academic reports ×2 (§9.4.2 sections + user-manual sections + contradiction-choices narrative + screenshots + sibling links) — C, review E+AG, approve I. DoD: `check_submission.py` README items green.
- ☐ **M8-2** KNOWN_LIMITATIONS.md + SELF_GRADE.md (`self_grade.py` output; code-quality only) — C, approve I.
- ☐ **M8-3** Full checklist sweep (`check_submission.py` fully green both repos; guidelines §17 + App C table 6) — C+I.
- ☐ **M8-4** Annotated tags `v1.0-submission` pushed both repos; Moodle per-member submission + PDF form + group ID (OI-1 resolved) — I.
- ☐ **M8-5** Final doc↔repo alignment audit (README numbers vs tree; PROMPTS.md truthful/complete) — C+I. DoD: zero contradictions found.

## Standing (every phase)

- ☐ **S-1** PROMPTS.md per PR (committed work only) — C.
- ☐ **S-2** Conventional commits; branch→PR→AG review→squash; never push main — all.
- ☐ **S-3** TODO statuses updated as work lands — C.
- ☐ **S-4** Risk register reviewed at each milestone exit (PRD §10) — I+C.
- ☐ **S-5** No email leaves draft without I's explicit per-send word — I (mechanical interlock + rule).
