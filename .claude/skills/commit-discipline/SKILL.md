---
name: commit-discipline
description: |
  Use this skill before creating any git commit. Triggers include:
  "ready to commit", "let me commit", "git commit", "stage the changes",
  "what should I include in this commit", "let's commit this", "time to commit".
  Always apply before staging files or running git commit.
---

# Commit Discipline

Enforces atomic commits, Conventional Commits format, and pre-commit verification.

## Pre-flight checks (run before staging)

1. **Verify you're not on `main`:** `git branch --show-current`.
   If `main` → STOP. Create a feature branch: `git checkout -b <type>/<short-name>`
   (e.g. `chore/m0-bootstrap`, `feat/domain-rules`).

2. **Check the diff size:** `git diff --stat` — target ≤ 300 changed lines; split by concern if larger.

3. **Tick TODO items:** if this commit completes a `docs/TODO.md` checkbox, tick it in the same commit.

4. **Docstrings:** any new public function/class has a docstring (params, returns, raises).

5. **Mirror discipline (thief repo only):** if the diff touches `src/copthief_core/`,
   `.claude/skills/`, `.github/workflows/`, `scripts/`, or `docs/REVIEW_PROCESS.md` — STOP.
   Those change only in the police repo and arrive here via `sync: core from police@<sha>`.

## Commit message format (Conventional Commits)

```
<type>(<scope>): <subject>

<optional body explaining WHY, referencing TODO ids>

<optional footer (Co-Authored-By, Closes #N)>
```

- **Types:** `feat | fix | docs | refactor | test | chore | perf | style | ci | sync`
- **Scopes:** `domain | wire | peer | infra | strategy | report | gui | sdk | shared | police |
  thief | arena | scripts | config | docs | ci`
- **Subject:** ≤ 72 chars, imperative, no trailing period.

Every commit authored by the agent ends with the current authoring model's co-author trailer:
```
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

## Pre-commit hooks (`.pre-commit-config.yaml`, run automatically)

`ruff check --fix` · `ruff format` · `mypy --strict src/` · `check_file_sizes.py` ·
`check_anti_patterns.py` · `check_no_hardcoded.py`.
If any fail, the commit aborts. Fix, re-stage, re-commit. **Never `--no-verify`** unless a
documented emergency is recorded in `docs/PROMPTS.md`.

## Anti-patterns to refuse

- WIP / unfinished work to `main` → feature branch instead.
- Vague messages ("update", "fixes") → require a Conventional Commit.
- Refactor bundled with a feature → split.
- Secrets, `.env`, OAuth artifacts (`client_secret*.json`/`token*.json`), leaked paths, or
  `"AI Agent"` authors.
- A commit that changes wire format / canonicalization / hashing without regenerating the kit
  conformance checks (CLAUDE.md §1 #13).

## Verify before signaling success

`git log -1 --format=fuller` — confirm author/committer, subject format, and intended file list.
