# TODO — Cops-and-Robbers P2P Race

> **Status: APPROVED (Phase 2 gate, 2026-07-16).** **This copy: the thief repo (role package `copthief_thief`).**
> Living document: checkboxes tick as work
> **lands on `main`**, never as aspiration. Statuses: ☐ not started · ◐ in progress · ☑ done.
> Owner key: **I** = Imree (drives, approves, operates sends/arming) · **C** = Claude (authors
> code/docs under I's direction) · **E** = Eyal (reviews, per-task ownership) · **AG** =
> Antigravity (cross-model PR review). Every task's DoD includes: CI green, ≤150-line files,
> tests per TDD, reviewed PR. ⚑ = role-repo-specific task.
>
> **Entry discipline (truth-pass, 2026-08-08):** an entry is a status plus one-to-three lines
> and pointers. Proof lives in `docs/evidence/`, decisions in ADRs, narrative in PR threads and
> `git log` — never here. A ☑ entry that grows past three lines gets compressed, not extended;
> the full pre-compression dossiers remain in this file's git history (`git log -p docs/TODO.md`).
> Shared-core milestones are led cop-side and arrive here via the sync ritual — the cop repo's
> TODO is the ledger for those; this file records thief-side work and thief-relevant status.

## Phase M0 — Process bedrock *(gate: PRD/PLAN/TODO approved in repo form)*

- ☑ **M0-1** Scaffold both repos (uv, pyproject, ruff/mypy/coverage config, empty `src/` layout per PLAN §3) — I+C.
- ☑ **M0-2** Port + adapt CI workflows from HW6 (keyless gates) — C, review E. Each gate demonstrably fails on a seeded violation.
- ☑ **M0-3** `scripts/sync_core.py` + `sync_manifest.json` + CI manifest gate — C, review AG.
- ☑ **M0-4** CLAUDE.md ×2 — C, approve I.
- ☑ **M0-5** Port `.claude/skills/` + `docs/REVIEW_PROCESS.md` — C.
- ☑ **M0-6** Land approved PRD/PLAN/TODO as `docs/` in both repos (⚑ role deltas applied) — C, approve I.
- ☑ **M0-7** `docs/adr/0001-sync-mirror.md` + `0002-reference-reuse.md` — C.
- ☑ **M0-8** `scripts/check_submission.py` skeleton — C. Runs in CI as non-blocking report.

## Phase M1 — Walking skeleton *(PRD_engine + PRD_crypto precede code)*

- ☑ **M1-1** `docs/PRD_engine.md` + `docs/PRD_crypto.md` — C, approve I.
- ☑ **M1-2** `domain/board+rules+scoring` (config-driven, App F guard) — C, review E/AG.
- ☑ **M1-3** `domain/crypto` from kit CORE + kit vectors as CI fixtures — C.
- ☑ **M1-4** `domain/state machine` — C. Property tests reject all illegal transitions.
- ☑ **M1-5** `wire/` dataclasses + validation — C.
- ☑ **M1-6** `infra/mcp` server + client + in-process fake; `peer/` minimal loop — C, review AG. Observed on the lead repo 2026-07-17 (`docs/evidence/m1-p2p-match.md` there).
- ☑ **M1-7** `sdk/` facade + CLI entry — C.
- ☑ **M1-8** JSONL logger — C.

## Phase M2 — 🚦 Oracle spike (go/no-go gate)

- ☑ **M2-1** Reference peer as oracle; Cloudflare named tunnel, both hostnames — I+C. (Lead evidence + ADRs live cop-side; our thief peer played pairing 2.)
- ☑ **M2-2** Both role pairings vs the live reference: mutual audit Verified OK both directions; our thief answered 35 straight capture claims (SQ2 live) — I+C.
- ☑ **M2-3** SQ1/SQ2/SQ3 answered in writing (cop repo spike notes §3/§6) — C.
- ☑ **M2-4** ADR-0003 + ADR-0006 (cop repo, lead for shared ADRs) — C.
- ☑ **M2-5** **GO/NO-GO — GO, 2026-07-18** (recorded in the cop repo's spike notes) — I.

## Phase M3 — Perception + arena

- ☑ **M3-1** `docs/PRD_scent.md` + `docs/PRD_belief.md` — C, approved I (cop PR #16; PRDs live in the lead repo).
- ☑ **M3-2** `domain/scent` (kit-pinned form; ADR-0004) — C.
- ☑ **M3-3** `domain/belief` exact Bayes filter — C, review E.
- ☑ **M3-4** Gazetteer + hint templates; injection-safety tests — C.
- ☑ **M3-5** Baseline brains via BrainBase seam — C.
- ☑ **M3-6** Arena harness + champion regression gate in CI — C, review E.
- ☑ **M3-7** 🚦 **ADR-0004 revision — DECIDED: REVISE** (I, 2026-07-18): second named scent model `multiplicative_book_v1`, pair-locked + refusal rule. Full record in ADR-0004 v2 + league coordination notes.
- ☑ **M3-8** Named scent models — BUILT cop-side (gate PR #56 there), mirrored here: six kit registrations verbatim, `scent_model_sha256` at negotiate (SPEC §7 truth table), model hash sealed at step 0. The book model's belief cost (hit-rate 98%→17%) was later addressed by M7-14's innovation fix.

## Phase M4 — Observability

- ☑ **M4-1** `docs/PRD_gui_replay.md` — C, approved I (cop PR #24; PRD lives in the lead repo).
- ☑ **M4-2** Live GUI (heatmap + turn banner; local truth only) — C (cop PRs #25/#26, core synced). ⚑ Thief-window screenshot for THIS repo's README rides M8-1.
- ☑ **M4-3** Replay verifier — C, review AG (cop PR #27, core synced; rule-19 mutation matrix runs in this repo's CI too).
- ☑ **M4-4** Belief-vs-truth overlay + belief-error curve export — C (cop PR #28, core synced).

## Phase M5 — Intelligence ⚑

- ☑ **M5-1** ⚑ `docs/PRD_thief_brain.md` — C, approved I (thief PR #20 + cop PR #30, approved together).
- ☑ **M5-2** ⚑ PoliceBrain — a POLICE-repo deliverable, delivered there (its PRs #31/#32, 75% DoD; role brains never mirror). Tracked here only for the phase's symmetry.
- ☑ **M5-3** ⚑ ThiefBrain: region-survival + articulation awareness + deception timing — C, review E/AG (PRs #21/#22). DoD observed, CI-blocking: 25/32 = 78% survival vs ref-police (floor 60%); candid greedy-tie note in `docs/evidence/m5-arena.md`.
- ☑ **M5-4** Genetic tuning (thief run): 78%→84% off-suite, breaking the M5-3 greedy tie; evolved weights deployed as config. `docs/evidence/m5-ga.md`.
- ☑ **M5-5** Post-audit opponent profiling — built cop-side (its PR #38), mirrored core + `PeerSession(hint_trust=…)` seam apply identically here.
- ☑ **M5-6** Template-bank A/B — measured HERE, winner `classic` shipped in `game.toml`; lie efficacy real but tiny (timing fires when the tracker is already near-certain). `docs/evidence/m5-template-ab.md`.
- ☑ **M5-7** `notebooks/results_analysis.ipynb` committed WITH outputs incl. the A/B table; renders-clean pin permanent CI (PR #26).

## Phase M6 — Reporting & fairness rail

- ☑ **M6-1** `docs/PRD_reporting.md` + `docs/PRD_gatekeeper.md` — approved I (cop PR #43; PRDs live cop-side).
- ☑ **M6-2** Four artifact schemas + writers (cop PR #44, via sync); conformance battery mirrored. Consensus signature = spaced-separator dumps, sign-then-insert (credit Alon).
- ☑ **M6-3** Step-0 declaration builder + signing (cop PR #45, via sync); real-HEAD pin runs per-repo.
- ☑ **M6-4** Gmail rail (cop PR #47, via sync) — this repo shares the single team sending identity; no separate account or consent. Draft posture superseded for counted play by M7-6.
- ☑ **M6-5** Gatekeeper (cop PR #46, via sync + this repo's `rate_limits.json` parity).
- ☑ **M6-6** Series runner (cop PR #48, via sync).
- ☑ **M6-7** Chaos drill harness + watchdog (cop PR #50, via sync); battery is mirrored permanent CI.
- ☑ **M6-8** COST.md + token accounting (cop PR #49 + this repo's COST.md parity).

## Phase M7 — League ops *(nothing announced unless true of the tree)*

> Shared-core M7 milestones (M7-7..M7-15, M7-17..M7-19, M7-22..M7-29, M7-31..M7-45, M7-53, M7-54)
> were led cop-side and arrived here via sync commits — the cop TODO is their ledger; `git log`
> here names each sync. Below: thief-led milestones + items with thief-side status of their own.

- ◐ **M7-0** Wire-shape mutual ADR — text landed cop-side as ADR-0010 (PROPOSED) + addendum; **signatures never collected, and the counted series vs anrbj666 played and cross-agreed anyway (M7-41). Disposition: no longer a blocker; close-or-co-sign is an M8 call (cop-led).**
- ◐ **M7-1** Sparring host — safety half arrived via sync 2026-07-22 (guard refuses tuned weights of either role + any mail recipient; `config-sparring/` git-ignored here). **Deployment (OI-4) + 24h DoD never happened; league floor met without it. Disposition: M8 call — deploy or close as not-pursued (KNOWN_LIMITATIONS candidate).**
- ☐ **M7-2** Kit additions — **status unverified from this repo**; several items believed landed by kit-side sessions. Verify against the kit repo before ticking or dropping (cop-led).
- ☑ **M7-3** League outreach + first external friendly 2026-07-25 (imreeyal 75–35 vs anrbj666, all audits clean, one auto-report to both teams). Lead evidence cop-side (`docs/evidence/m7-3-first-external-friendly.md` there).
- ☑ **M7-4** First counted series — discharged by M7-41 (cop TODO; ledger advanced here in sync #69).
- ☑ **M7-4b** Live-series machinery (sealed `--sub-game` index — the defect bit THIS repo directly on odd sub-games; `summary_from_log`/`series_from_logs`; `sdk/live_series` owner) — via syncs; `num_games` 1→6 parity committed here.
- ◐ **M7-5** Counted series vs distinct teams — **two played, App F pass floor met** (anrbj666 lost 30–90; uoh-sqak WON 60–40, +10 diversity). Third candidate best2934 blocked on a mutual code-level handshake gap (their negotiate carries no kit-CORE terms/nonce/signature; both sides informed 2026-08-08).
- ☑ **M7-6** 🚦 Email posture correction (cop ADR-0008) — mirrored here as thief PR #35 (main `9ab4dce`): automatic send, recipient = the authorization, `gmail.send`-only shared token, this repo's CLAUDE.md #16/§4 amended.
- ☑ **M7-7** 🚦 Real-tunnel kill-drill defects — fixed cop-side, closed here via sync (all four in mirrored core; `state_*.json` git-ignore parity here).
- ◐ **M7-8** At-least-once inbound tolerance — code half closed here via sync (`InboundSequencer`; `[network] inbound_buffer_limit` + v1.01 parity committed here). **Live us→them-dedup and reorder halves never drilled; two clean counted series retired the practical risk. Disposition: accepted residual — KNOWN_LIMITATIONS candidate at M8.**
- ☑ **M7-9** `RunMode` split (cop ADR-0009, via sync); CLI flags residual discharged via sync.
- ☑ **M7-10** Handshake pairing + redelivery + port guard — via sync; **the Alon/Renat team confirmed their half on the wire 2026-07-24, so this is closed both directions.**
- ☑ **M7-16** ⚑ Thief book-v1 retune: anti-camping emerged from selection (`ramp_start_fraction` → box floor 0.3 on the overlay); deployed on `[strategy.thief.multiplicative_book_v1]`, base table untouched. Evidence: `docs/evidence/m7-16-thief-bookv1-retune.md`.
- ☑ **M7-18** ⚑ The evader reads capture claims (core `note_claim` via sync): peer-path cop-tracking here 0.502→0.994; survivals 8→21 vs both chasers, points +18% — information, not tuning. Evidence: `docs/evidence/m7-18-claim-channel.md`.
- ☑ **M7-19** Quiet cop — core via sync, **inert on this side by construction** (only a police peer emits claims; no `claim_threshold` set here). An opponent adopting it takes back most of M7-18's edge (0.94→0.43 tracking) — accepted.
- ☑ **M7-21** ⚑ Informed-thief retune — deployed on the book-v1 overlay (gate wins both physics on the visible genes). ⚠ Dated correction 2026-08-02 (M7-30): the `w_articulation` headline was NOT measurable by the instrument (inert in referee mode) — free drift, not a finding; visible-gene gains stand. Full correction in `docs/evidence/m7-21-informed-thief.md` §0.
- ☑ **M7-30** ⚑ Thief-vs-walling retune — **NULL RESULT, not deployed** (fails the every-arm gate on `sealer-quiet`); the real finding was the referee instrument defect (barrier quota never fed → `w_articulation` inert, M7-21 headline corrected; fixed cop-side as M7-31). `SealerPoliceBrain` arms kept. Evidence: `docs/evidence/m7-30-thief-vs-walling.md`.
- ☑ **M7-46** ⚑ uoh-sqak thief losses diagnosed from their source (their cop moved AND walled — Barrier Law; raised with them, **they fixed it in two hours**): shipped `features.support_width` siege narrowing — 0/32→10/32 at their live tempo, signed start flips to survival; CI arena byte-identical; `sqak_apex` arm + keyless tempo pin. Merged in PR #72. Evidence: `docs/evidence/m7-46-sqak-thief.md`.
- ☑ **M7-47** ⚑ The flight ramp arms on KNOWING, not just the clock (`sharp_ramp_mass` 0.9 trigger beside the GA-tuned clock): best2934-police 18→32, every arm better-or-equal, CI arena byte-identical. Merged in PR #72. ⚠ Named follow-up not pursued: `config/ga.json` bounds `ramp_start_fraction` to [0.3, 0.95] — the useful values sit below the box. Evidence: `docs/evidence/m7-47-informed-ramp.md`.
- ☑ **M7-51** ⚑ Close-threat trigger: flee the argmax, not a cloud, inside `close_threat_distance` (2.0) — 0/32→6/32 vs uoh-sqak's fixed cop, signed start flips to survival, DoD 84%→88%; rejected alternatives kept as labelled negatives (incl. the fresh-peak decoder that zeroed our COP 45/64→0/64 — reverted cop-side). Merged in PR #73. Evidence: `docs/evidence/m7-51-close-threat.md`.
- ☑ **M7-52** 🏁 **SECOND COUNTED SERIES WON** 60–40 (4–2) vs uoh-sqak (2026-08-08) — App F pass floor met, +10 diversity; ledger advanced to 2 here (PR #74).
- ☑ **M7-53** Absorb the opponent's opening handover (via sync #75).
- ☑ **M7-54** A signature refusal names the construction (via sync #76).
- ☐ **M7-55** 🚦 Opponent identity at negotiate (cop-led, mirrored core): our `negotiate` accepts ANY caller — fix on the cop repo's `rescue/m7-opponent-identity`, **UNMERGED**; arrives here via sync once decided.

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
- ☐ **S-5** No email is ever sent to an address I has not configured for that run, and **never to the lecturer** without his explicit word — I (mechanical: the interlock refuses an empty recipient list, and refuses the configured `lecturer` address whenever `counted` is false). Reworded 2026-07-20 by ADR-0008 (this copy carried the stale pre-ADR draft wording until the 2026-08-08 truth-pass). Outreach mail keeps the original per-send rule — see the parent-workspace `CLAUDE.md`.
