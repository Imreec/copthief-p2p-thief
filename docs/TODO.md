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
- ☐ **M3-2** `domain/scent` (kit-pinned form; locked-model doc w/ numeric example; ADR-0004) — C. DoD: kit pheromone vectors + decay/emission tests green.
- ☐ **M3-3** `domain/belief` exact Bayes filter (motion×scent×hint) — C, review E. DoD: beats last-known-position tracker on belief-error in referee sims (PLAN §13 M3).
- ☐ **M3-4** Gazetteer + hint templates (map_area landmarks; ≤hint_max_words; intent flag wired to sealing) — C. DoD: our hints round-trip our parser; injection-safety tests (hostile hint corpus).
- ☐ **M3-5** Baseline brains (random, greedy-Manhattan) via BrainBase seam — C. DoD: full headless series in referee + peer modes.
- ☐ **M3-6** Arena harness (sdk consumer; seeded round-robin; tables; champion regression gate in CI) — C, review E. DoD: seeded reproducibility test; gate red on champion loss.

## Phase M4 — Observability

- ☐ **M4-1** `docs/PRD_gui_replay.md` — C, approve I.
- ☐ **M4-2** Live GUI (heatmap + turn banner; local truth only) — C. DoD: screenshot from a real game saved to assets/.
- ☐ **M4-3** Replay verifier (Verified OK / TAMPERED) — C, review AG. DoD: M2 log → Verified OK; mutated log → TAMPERED (both observed).
- ☐ **M4-4** Belief-vs-truth overlay + belief-error curve export — C. DoD: overlay rendered from a real audited game.

## Phase M5 — Intelligence ⚑

- ☐ **M5-1** ⚑ `docs/PRD_police_brain.md` (police repo) / `docs/PRD_thief_brain.md` (thief repo) — C, approve I.
- ☐ **M5-2** ⚑ PoliceBrain: expectimax over belief + barrier graph-surgery + claim policy — C, review E. DoD: ≥60% arena vs reference heuristic (cop role).
- ☐ **M5-3** ⚑ ThiefBrain: region-survival + articulation awareness + deception timing — C, review E. DoD: ≥60% arena vs reference heuristic (thief role).
- ☐ **M5-4** Genetic tuning runs (HW6 salvage adapted; weights → config) — C. DoD: improving fitness curve artifact committed.
- ☐ **M5-5** Post-audit opponent profiling (lie-rate, motion priors → next mini-game) — C. DoD: PLAN §13 M5 prior-shift test.
- ☐ **M5-6** Template-bank A/B in arena (deception efficacy metric) — C. DoD: measured table in notebook; winning bank shipped.
- ☐ **M5-7** `notebooks/results_analysis.ipynb` (arena + sensitivity + curves; LaTeX + citations) — C, review E. DoD: renders clean, committed with outputs.

## Phase M6 — Reporting & fairness rail

- ☐ **M6-1** `docs/PRD_reporting.md` + `docs/PRD_gatekeeper.md` — C, approve I.
- ☐ **M6-2** Four artifact schemas + writers (game_uid naming; canonical bytes = emailed bytes) — C, review AG. DoD: validated against reference `docs/sample-run/` shapes.
- ☐ **M6-3** Step-0 declaration builder (hardware, model, tokens, commit hash, game-count) + signing — C. DoD: real commit hash asserted in test.
- ☐ **M6-4** Gmail sender (send-only OAuth per App A; HW6 flow) + **draft default + arming interlock** — C, operate I. DoD: PLAN §13 M6 — report lands as draft; send path provably requires arming.
- ☐ **M6-5** Gatekeeper (quota → token bucket → DoS lock; `rate_limits.json` ≥ signed minimums asserted) — C. DoD: synthetic-load test queues, never crashes; 429 backoff honored.
- ☐ **M6-6** Series runner (`num_games`, per-game config commit, roles) — C. DoD: full local series produces 4 valid artifacts.
- ☐ **M6-7** Chaos drill harness (PLAN §10 drills) — C, review E. DoD: every drill's defense observed; logs committed.
- ☐ **M6-8** COST.md + token accounting on every LLM path — C. DoD: 0-token series proven by log.

## Phase M7 — League ops *(nothing announced unless true of the tree)*

- ☐ **M7-1** Sparring host deployed (both roles, generic brain, draft-pinned; OI-4 decided) — I+C. DoD: external reachability check passes 24h.
- ☐ **M7-2** Kit: wire-contract page + JSON-schema fixtures + audit fixture (incl. tampered record) + **pre-match checklist & netcheck script** + SPEC §4 naming clarification — C, review E. DoD: kit CI green; I merges.
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
