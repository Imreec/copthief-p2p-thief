# Prompt Engineering Log

> Truthful, per-PR entries for **committed** work only (CLAUDE.md §7). Development prompts —
> runtime agent prompts live in source. Format: PR · driver/reviewer · what was asked · outcome.

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
