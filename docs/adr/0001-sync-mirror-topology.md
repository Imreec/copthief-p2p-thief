# ADR-0001 — Two-repo topology: mirror + sync-check, police repo leads

**Status:** Accepted (Phase 1 grill, 2026-07-16; approved by Imree).

## Context

The book mandates two separate submission repos (cop, thief), each self-contained with its own
README/PRD/PLAN/TODO/config and a real development history "so the examiner can reconstruct the
working process." ~85% of the code (engine, protocol, crypto, reliability, GUI, reporting) is
role-agnostic; only the brains, configs, and README narratives differ. The reference
implementation is a single codebase running both roles — the two-repo rule is a submission
mandate, not an architecture claim.

## Decision

Shared code lives in `src/copthief_core/`, developed **only** in the police repo (lead) and
mirrored byte-identically into the thief repo by `scripts/sync_core.py`. A committed
`sync_manifest.json` (per-file SHA-256 + tree hash + source commit) is verified by CI in **both**
repos — any drift fails the build. Sync commits are honest history: `sync: core from
police@<sha>`. Mirrored paths: `src/copthief_core/`, `.claude/skills/`, `.github/workflows/`,
`docs/REVIEW_PROCESS.md`, `scripts/`. Role packages (`copthief_police`/`copthief_thief`),
`config/`, `docs/` (except REVIEW_PROCESS), and READMEs diverge freely.

## Consequences

Each repo stands alone for a grader; no third repo or submodule friction; dual-commit ceremony is
mechanized by the script and enforced by CI; the thief repo's core history is sync commits by
design (documented here and in its README).

## Alternatives considered

Third shared-core repo (submission repos no longer stand alone; extra grader access);
monorepo-with-export (synthetic history defeats the process-reconstruction mandate); fully
divergent codebases (double work, zero grade value).
