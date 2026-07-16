---
name: tdd-cycle
description: |
  Use this skill when implementing any new feature, function, class, or module. Triggers include:
  "implement", "let's build", "add a feature", "write a function", "create a class",
  "add a method", "let's code", "now build", "let's write".
  Always apply for any new code that has logic — skip only for pure config/data files.
---

# TDD Cycle (Red → Green → Refactor)

Strict test-first discipline. Coverage (≥85% global, ≥90% deterministic core) emerges as a
side effect.

> **Project note:** the pure modules (`domain`, `wire`, `report`, core parts of `strategy`) are
> fully TDD-able keyless. The live layers (`infra`: FastMCP transport, Gmail, LLM providers,
> tunnel) are thin adapters — exercised with a **mock LLM + in-process MCP fake** in CI, and by
> opt-in live runs (`@pytest.mark.live`, excluded from CI). Put the *logic* in pure modules so
> it's testable; keep the adapters thin.

## The cycle (one concern at a time)

### RED — write the failing test first
1. Create/open the matching `tests/<area>/test_<thing>.py`.
2. Write a test describing **behavior**, with a descriptive name
   (`test_barrier_on_thief_cell_is_capture`, not `test_barrier`;
   `test_commit_binds_intent_flag`, not `test_commit`).
3. Run it — it MUST fail meaningfully (missing attr, wrong value), not an unrelated import error:
   `uv run pytest tests/domain/test_rules.py::test_barrier_on_thief_cell_is_capture -xvs`
4. **Commit RED:** `git commit -m "test(domain): failing test for barrier-on-thief capture"`

### GREEN — minimal code to pass
1. Write only enough to pass — nothing the tests don't demand.
2. Re-run the test (`1 passed`), then the suite (`uv run pytest -x`).
3. **Commit GREEN:** `git commit -m "feat(domain): barrier on thief's cell captures (book ch.3)"`

### REFACTOR — improve without changing behavior
Extract helpers, improve names, add docstrings, keep files ≤ 150 lines. Tests stay green. Optional.

## Rules

1. One concern per cycle — don't implement two functions off one test.
2. No skipping RED. Code-first → delete, write the test, re-implement.
3. Verify each phase by reading pytest output, not by trusting it.
4. No `pytest.skip` to defer work — write it now or remove it.
5. Coverage is a side effect, not the goal.
6. Behavior pinned by the book cites its source in the GREEN commit (chapter / App F key).

## Unit vs integration vs conformance vs live

- `tests/unit/<area>` — one pure module in isolation (rules, scoring, scent, belief, crypto).
- `tests/conformance` — the kit CORE vectors as fixtures (byte-level interop; CI-blocking).
- `tests/integration` — composition (two peers + mock LLM + in-process MCP fake → full mini-game).
- `@pytest.mark.live` — real LLM / network / deployed server; excluded from CI, run manually.

## Verify before signaling success

`make test` and `make lint` both green. If either fails, the cycle isn't complete.
