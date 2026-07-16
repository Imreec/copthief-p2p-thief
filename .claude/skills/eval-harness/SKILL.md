---
name: eval-harness
description: |
  Use this skill when building, running, or reasoning about the project's evals — the layer that
  proves the system *behaves correctly* (interop holds, audits pass, strategy actually wins),
  distinct from tests that prove the code *runs*. Triggers: "eval", "structural eval", "validity
  check", "conformance", "does the audit pass", "arena", "win-rate", "is the brain better",
  "chaos drill". Apply whenever a change could affect interop bytes, audit outcomes, or
  strategy strength.
---

# Eval Harness (validity beyond tests)

Tests prove the code *runs*; **evals** prove the system produces **valid, evidenced** results.
Three layers, keyless in CI except the last. **Inversion from HW6: strategy strength is graded
here** — the arena is a first-class eval, not a nice-to-have.

## Layer 1 — structural invariants (keyless, deterministic, in CI)

Code-based invariants on the pure core. Each must hold on **every** run:

1. **app-f-guard** — the config loader rejects any agreement that alters a fixed App F value or
   lowers a minimum; defaults apply when no agreement exists.
2. **capture-triad** — capture fires on: cop landing + claim, barrier placed on the thief's
   cell, thief imprisoned with no legal move. All three, exactly.
3. **barrier-rules** — placement only on cop's own/orthogonally-adjacent cell, only instead of
   moving, ≤ `max_barriers`, impassable to both, truthfully declared.
4. **scent-locked-model** — emission + decay reproduce the cryptographically locked model
   byte-for-byte (kit-pinned reference form; the book-prose divergence is ADR-0004).
5. **commit-binds** — a reveal that changes state, move, intent, *or* nonce fails verification.
6. **canonical-form** — `sort_keys`, `ensure_ascii=False`, compact separators; Hebrew hints and
   shortest-round-trip floats survive (kit CORE).
7. **state-machine-legality** — every illegal transition raises; terminal states terminal.
8. **scoring-table** — all six scoring values + tie rule come from config and sum per the book.

## Layer 2 — conformance + replayed protocol (keyless, in CI)

- `tests/conformance/` re-derives **every kit CORE vector** (canonical, commit, terms signature,
  game_uid, pheromone). Any wire/hash change regenerates these BEFORE merge (CLAUDE.md §1 #13).
- Record-replay: real transcripts (oracle spike, friendlies) committed as fixtures and replayed
  through wire-validation → state machine → audit. Re-record on any protocol change — a stale
  fixture that passes is worse than no test.
- **Chaos drills replayed:** each scripted fault (tunnel drop mid-commit, deadline-edge delay,
  malformed/duplicate message, oversized hint, tampered audit record) asserts its specific
  defense fires.

## Layer 3 — live evidence + the arena (committed artifacts)

- **Arena (referee mode):** seeded round-robin of brains; baselines = random, greedy-Manhattan,
  the reference's shipped heuristic. **Champion regression gate in CI: a new brain must not lose
  to the previous champion.** Win-rate/points tables + sensitivity sweeps export to
  `notebooks/results_analysis.ipynb`.
- Live games can't run in CI. Validity = committed logs: oracle-spike transcripts, friendly
  cross-audit logs, belief-vs-truth overlays + belief-error curves, fitness curves from genetic
  tuning, 0-token COST evidence.

## How to run

```bash
uv run pytest tests/unit tests/conformance tests/integration -v   # what CI runs
uv run python -m arena run --seeded                                # arena (from M3)
uv run python scripts/check_submission.py                          # living checklist
```

## The discipline (non-negotiable)

A failing structural eval or conformance vector means the system is wrong — **fix before
merge**. A result claim without a committed log/artifact is **not reported** (or goes to
KNOWN_LIMITATIONS.md). Never delete an eval to go green; never claim a win-rate without the
seeded arena table; never claim interop without the cross-audit log.
