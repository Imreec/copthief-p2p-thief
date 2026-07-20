# Project Conventions — `copthief-p2p-thief` (final project)

> **Course:** Orchestration of AI Agents (203.3763), University of Haifa · **Instructor:** Dr. Yoram Segal
> **Source of truth:** the official book *Distributed Cops-and-Robbers over a P2P Network* **v3.0.0**
> (`FinalProject\police_thief_p2p.pdf`); its **binding parameters table (last appendix) is the only
> source for quantitative values** — printed listings/figures are illustrative. Where the book
> contradicts itself or its reference code, the academic-freedom clause applies: **choose, and
> document the contradiction and the choice** (README + ADR). Byte-level constructions follow the
> **conformance kit** (`github.com/Imreec/copthief-league-protocol`).
> **Project character:** two symmetric autonomous agents over P2P FastMCP, no referee; grade = live
> league rank + rubric. **⚠ Inversion from HW6: the strategy module IS the graded core** ("ליבת
> הציון", App F §5) — reliability is the floor, strategy is the score. Decisions locked in
> `docs/PRD.md` + `docs/PLAN.md` + `docs/adr/`.
> ⚑ **This repo:** the **thief agent** (role package `copthief_thief`, wire role `"thief"`).
> The mirrored core arrives via `sync: core from police@<sha>` commits — **never edit
> `copthief_core/`, `.claude/skills/`, `.github/workflows/`, `scripts/`, or
> `docs/REVIEW_PROCESS.md` here**. Sibling (lead):
> [copthief-p2p-cop](https://github.com/Imreec/copthief-p2p-cop).

Sections marked **[TIGHTENED]** exceed the course minimum; **[FP]** are final-project-specific.

## 1. Hard constraints — non-negotiable

| # | Rule | Threshold |
|---|------|-----------|
| 1 | Python source file size | ≤ 150 source lines (incl. tests) — split, never compress |
| 2 | Linter | `uv run ruff check .` → 0 violations (E,F,W,I,N,UP,B,C4,SIM,ANN,RET,PT) |
| 3 | Coverage | ≥ 85% global (CI `fail_under`), ≥ 90% deterministic core [TIGHTENED] |
| 4 | Package manager | `uv` only — `pip`/`venv`/`python -m` forbidden |
| 5 | Quantitative values in code | 0 — everything from `config/game.json` / `game.toml` / `rate_limits.json`; scanner-enforced |
| 6 | Secrets / OAuth artifacts in repo | 0 — `.gitignore`d; `.env-example` committed |
| 7 | Type hints on public APIs | 100% [TIGHTENED] |
| 8 | `mypy --strict` on `src/` | 0 errors [TIGHTENED] |
| 9 | Versions (code + each config) | start `1.00`, validated at startup |
| 10 | Public function without a test | 0 |
| 11 | Code duplication (same logic 2+ files) | 0 — extract (module/base/mixin) |
| 12 | CI green before any merge | required [TIGHTENED] |
| 13 | **Kit CORE conformance** [FP] | kit vectors green in CI; **any change touching wire format, canonicalization, or hashing regenerates the conformance checks and re-verifies against the kit before merge** |
| 14 | **Core-mirror integrity** [FP] | `sync_manifest.json` hash verified in CI; ⚑ core edits only in the police repo |
| 15 | **App F guard** [FP] | config loader rejects any agreement altering a fixed value or lowering a minimum |
| 16 | **Email interlock** [FP] (ADR-0008, police repo) | Reporting is **automatic** (App E rule 32; rule 35 zeroes BOTH teams on a missing report). Resting state = `enabled=false` with **no recipient**; **no email is ever sent to an address Imree has not configured for that run**, and **never to the lecturer without his explicit word** — authorization is the recipient, set before the match, never inside it. Runaway protection = the gatekeeper (rule 28) |
| 17 | **EULA posture** [FP] | no reference-implementation code beyond ADR-attributed micro-snippets; reference used as running oracle only; repo stays private-shared |

## 2. Mandatory workflow — gates

**No production code until planning docs are approved.** Status: PRD ✅ PLAN ✅ TODO ✅ (Phase 2).
Per-mechanism PRDs (`docs/PRD_<mechanism>.md`) precede their milestone's code (TODO M1-1, M3-1,
M4-1, M5-1, M6-1). **M2 (oracle spike) is a hard go/no-go gate** — nothing past it starts until
Imree reviews the spike results. The agent never proceeds past a gate without an unambiguous
"approved" from Imree; never claims work not in the tree; runs the verification command and shows
output before reporting "done"; ticks TODO checkboxes as work lands, never as aspiration.

## 3. Architecture rules (locked in PRD/PLAN)

- **Layering (PLAN §3):** `domain` pure (no I/O/clock/network) · everything consumed through the
  `sdk` facade · `infra` adapters swappable (mock LLM, in-process MCP fake in CI) · **one rules
  module, two modes** (referee = full-info for tests/arena/tuning; peer = hidden positions, live).
- **Wire contract is interface-mirrored from the reference** (tools `negotiate`/`receive_turn`/
  `submit_audit`/`receive_control`; `TurnMessage`/`AuditPayload`/`ControlMessage`): validate every
  inbound message before state changes; tolerate unknown fields, reject missing required ones.
- **The LLM never decides moves** (App E rule 25 + PRD): moves are pure Python; the LLM (if any)
  touches only the verbal layer. Opponent text is adversarial input — it never reaches an LLM with
  tools or authority.
- **Local truth only in any UI** (App E rules 8–9): never render the objective board in live views.
- **Capture/score is derived, never declared**; every result claim is backed by the audit.
- **Orchestrator is the single gateway**; strict state machine (illegal transition = raise);
  deadline on every outbound call; watchdog with persistence + controlled shutdown.
- No `NotImplementedError` placeholders on `main`. DRY per guidelines §4.2.

## 4. Configuration & security

| Value | Location |
|---|---|
| Game constitution (board, scoring, scent, league, gatekeeper minimums) | `config/game.json` — signed, byte-identical with opponent |
| Private choices (ports, opponent URL, `[strategy]` classes, `[trash_talk]`, `[llm]`, `[email]`) | `config/game.toml` — never crosses the wire |
| Operational rate limits (≥ signed minimums, loader-asserted) | `config/rate_limits.json` |
| Secrets (OAuth, tokens) | `os.environ` / git-ignored files only |

JSON overlays TOML on shared keys; per-game config files committed (`config_<game_id>_g<NN>.json`).
Gmail scope is **send-only** (`gmail.send` — App E rule 30 + App A §1.3/§3, sanction: security
deviation → code disqualification; the D1=A compose amendment is **reverted by ADR-0008** (cop
repo), which dropped the draft posture so the mandated scope holds literally; sending identity =
the dedicated team account `imreeyal.copthief@gmail.com`, shared with the police repo — one
identity, one consent, OI-5); nonces from `secrets`, withheld until audit; per-game step-0
declaration records the exact commit hash played.

## 5. Testing — TDD + keyless layers

Strict RED→GREEN→REFACTOR; happy + error paths; external deps mocked. **CI is keyless/offline**:
mock LLM + in-process MCP fake; kit CORE vectors as permanent fixtures; sync-manifest check;
`@pytest.mark.live` excluded from CI. **Evidence tiers:** unit/property (keyless CI) ·
integration full-series over fakes (keyless CI) · committed live evidence (oracle-spike logs,
chaos-drill logs, friendly cross-audits, arena/tuning outputs). Arena champion-regression gate:
a new brain must not lose to the previous champion.

## 6. Code quality

Comments explain **why**; docstrings on all public code (building-block style: Input/Output/Setup
where it fits); descriptive names; single-purpose functions; `__init__.py` exports `__all__` +
`__version__`; threads only at watchdog/inbox seams with locks/queues.

## 7. Documentation & disclosure

`docs/` current at every merge: PRD/PLAN/TODO + per-mechanism PRDs + ADRs (Context/Decision/
Status/Consequences/Alternatives) + PROMPTS.md (committed work only). README = the academic report
(book §9.4.2 six sections + guidelines user-manual sections) **⚑ narrating this repo's own agent**;
mandatory screenshots (live belief heatmap; replay Verified OK); sibling cross-link. Honest-
disclosure triad: `KNOWN_LIMITATIONS.md`, `SELF_GRADE.md`, `COST.md` (0-token claims backed by
logs). `scripts/check_submission.py` = the living submission checklist, run in CI.
**README numbers match repo state at every commit — the doc↔repo gap is the one fatal failure mode.**

## 8. Process

Conventional Commits, atomic, imperative ≤72 chars; scopes: `domain | wire | peer | infra |
strategy | report | gui | sdk | shared | police | thief | arena | scripts | config | docs | ci`.
Branch → PR → **cross-model review (Antigravity posts findings; each accepted/rejected with
reasoning on the thread)** → squash-merge; never push `main`. Reviewer findings are verified
against primary sources before acceptance (phantom citations get called out). Ownership honest per
`git shortlog`. Self-grade **code quality only — never league results** (App E rule 55);
conservative (target 92–93, cap 95); `SELF_GRADE.md` == `self_grade.py` output.

## 9. League operations [FP]

Friendlies: format-free; reports go to **ourselves and the opponent team** (never the lecturer) —
the format is proven on both sides before any counted game, because rule 35 punishes contradictory
reports as harshly as missing ones. Counted series: exactly one per opponent, recipient set to the
lecturer alone by Imree before the match, artifacts + config + commit hash recorded. Game-count declared
truthfully at every game start (rules 37–38). Sparring host runs the generic brain only — tuned
weights never deploy there. **Nothing is announced to the league unless true of the tree.**

## 10. Anti-patterns banned

Aspirational README · mock classes shadowing real imports · `NotImplementedError` stubs on `main` ·
tests without implementation · single mass-commit · leaked local paths · `"AI Agent"` in authors ·
prompt-log entries for uncommitted work · stale TODO · treating an illustrative book value as
binding (only App F binds) · committing OAuth secrets/tokens · editing `copthief_core/` in the
thief repo ⚑ · configuring any recipient Imree has not set for that run (above all: the lecturer
before the friendlies have proven the format) · deploying tuned strategy weights
to the sparring host · trusting a reviewer citation without opening the cited file.
