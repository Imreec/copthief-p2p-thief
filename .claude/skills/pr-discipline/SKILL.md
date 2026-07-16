---
name: pr-discipline
description: |
  Use this skill when ready to open a pull request or merge to main. Triggers include:
  "open a PR", "create pull request", "ready to merge", "let's review",
  "ship this", "time to merge", "submit for review", "let's get this into main".
  Always apply before invoking gh pr create or merging.
---

# PR Discipline

Enforces a clean PR workflow: up-to-date branch, green checks, full description, cross-model
review, README/TODO sync. **Nothing reaches `main` except via an approved, squash-merged PR.**

## Pre-PR checks (run before opening)

1. **Branch up to date with main:**
   `git checkout main && git pull --ff-only && git checkout - && git rebase main`
   Resolve conflicts, then `git push --force-with-lease` if rebased.

2. **All quality checks green:** `make grade` (ruff + format + mypy + sizes + patterns +
   hardcoded + sync-verify + tests + submission report). If any fail — STOP, fix, commit, push.

3. **README current** — and honest: the README is the report; no claims of unmeasured results.

4. **TODO current:** tick every checkbox this branch completes, in the relevant commit.

5. **Self-review the diff** on GitHub compare view: every intended file present, no stray files
   (`.DS_Store`, IDE configs, **OAuth secrets/tokens**), no debug `print()`, no hardcoded values,
   tests cover new logic + edge cases.

## Opening the PR

`gh pr create --base main --head <branch>` — the template loads; fill **every** section
(summary, PRD/PLAN/TODO traceability, changes, checklists). End the body with the Claude Code
trailer.

## After opening

- **Wait for CI.** Red CI → read the failure, fix locally, push. Never merge red.
- **Cross-model review is a real gate.** A separate model family reviews and posts findings.
  For each finding: **open the cited file and verify the citation is real** (phantom citations
  get called out — see docs/REVIEW_PROCESS.md), then accept/reject with reasoning on the thread,
  apply accepted fixes on the branch, and reply documenting the resolution.

## Merging

- **Squash-merge** is the default: `gh pr merge <n> --squash --delete-branch`, then
  `git checkout main && git pull --ff-only`.
- If the PR touched mirrored paths (police repo): run `scripts/sync_core.py --sync` after the
  merge and commit the sibling's `sync:` commit.

## Post-merge

Update `docs/PROMPTS.md` with a brief, truthful entry for the shipped work (driver, reviewer,
outcome). Only log work that is actually committed.

## Anti-patterns to refuse

Open a PR without rebasing · skip `make grade` · merge with a vague description · merge red CI ·
force-push to `main` · merge before the cross-model review is addressed · leave the sibling
unsynced after a mirrored-path merge.
