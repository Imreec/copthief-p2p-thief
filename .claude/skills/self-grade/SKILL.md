---
name: self-grade
description: |
  Use this skill when ready to compute the final self-assessed grade for submission. Triggers:
  "self grade", "final grade", "ready to submit", "compute the grade", "self-assess",
  "grade ourselves", "submission check", "before we submit".
  Apply only at the end of the project, after all other work is complete.
---

# Self-Grade

Computes a defensible self-assessed grade with strict honesty. Target **92–93**, cap 95.

> **RULE 55 (book App E) — the frame for everything here:** the self-grade assesses
> **code quality only — never the league game result**. A self-grade based on match outcomes
> would corrupt the criterion. Win-rates belong in the README as evidence, not in this number.

## When to run

Only when: all PRs merged to `main`; CI green on `main`; both repos' README academic reports
complete with every figure embedded; committed logs back every result claim;
`KNOWN_LIMITATIONS.md` current; `scripts/check_submission.py --strict` green.

## How to compute

`scripts/self_grade.py` reads `config/self_grade.json` and prints the weighted breakdown.
`SELF_GRADE.md` prose must match the script output exactly (a mismatch is a doc↔repo gap).

## What gets graded (code quality dimensions, per PRD §11)

| Category | Weight | What's measured |
|----------|--------|-----------------|
| Architecture & orchestration patterns | 20 | Layering per PLAN §3, SDK facade, Orchestrator/state machine, referee+peer modes over one rules module |
| Protocol/crypto correctness & interop evidence | 20 | Kit CORE conformance, oracle-spike + friendly cross-audit logs, canonical-bytes discipline |
| Strategy-module engineering | 20 | Clarity, tests, tuning *methodology* (arena, genetic runs, profiling) — engineering quality, **not win-rate** |
| Reliability engineering | 15 | State machine, deadline tracker, watchdog, gatekeeper, chaos-drill evidence |
| Documentation & research artifacts | 15 | README report (both repos), notebook, ADRs incl. documented book contradictions, honest-disclosure triad |
| Process discipline | 10 | ruff/mypy/coverage/size gates, atomic PRs, cross-model review trail, truthful PROMPTS.md |

## Honesty rules

1. **Never report > 95 without explicit override + audit.** Script > 95 → re-run with harsher
   penalties; lower at least one judgment call.
2. **The grader is ground truth.** Target slightly below your honest assessment (think 94 → 92).
3. **Justification > number.** Per-category written justification required.
4. `KNOWN_LIMITATIONS.md` *is* the justification for the gap below 100 — documented limitations
   read as calibration, not modesty.

## Anti-patterns to refuse

Report > 95 without audit · grade league results (rule 55) · submit without KNOWN_LIMITATIONS
entries · submit with CI red on `main` · skip the justification text · backdate.

## Verify before submission

`make grade` green on `main` in **both repos** · `self_grade.py` output == `SELF_GRADE.md` ·
READMEs render on github.com with figures · **both repos private-shared with the lecturer**
(never flipped public — EULA posture, CLAUDE.md §1 #17) · cross-links + all four links present ·
`v1.0-submission` tags pushed · `docs/PROMPTS.md` truthful and complete.
