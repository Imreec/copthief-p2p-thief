# PRD — Cops-and-Robbers P2P Race (final project)

> **Status: APPROVED (Phase 2 gate, 2026-07-16), after cross-model review — see
> `docs/REVIEW_PROCESS.md`.** **This copy: the thief repo (role package `copthief_thief`).** Sibling (lead): [copthief-p2p-cop](https://github.com/Imreec/copthief-p2p-cop).
> Per-mechanism
> PRDs (`docs/PRD_<mechanism>.md`) are written just-in-time per milestone (guidelines §2.3 + the
> book's staged-PRD recommendation). Sources of truth: book v3.0.0 + binding parameters table
> (App F) > this PRD. Quantitative values appear here as their binding `game.json` field names
> (the book fixes the schema's English key names; App F fixes the values) —
> **every number is config-owned and loaded at runtime; nothing quantitative is hardcoded.**

## 1. Overview & context

Final project of *Orchestration of AI Agents* (Univ. of Haifa, Dr. Yoram Segal): two autonomous,
symmetric AI agents — **Cop** and **Thief** — play a hidden-position pursuit race over a real P2P
network. Each agent is simultaneously a FastMCP server and client behind a public tunnel; there is
no referee. Physics and honesty are enforced by a signed shared config ("constitution"), per-step
SHA-256 commit-reveal, and a mutual end-of-game audit. Grading is a **live league**: series against
other teams' agents, diversity-rewarded, computational-fairness-normalized, with mandatory
automated Gmail reporting.

**The problem:** build a distributed system that (1) never loses technically — a technical loss is
0/0 for both sides, so reliability is the floor; (2) wins mini-games through superior inference and
planning under partial observability; (3) proves everything — to the opponent (audit), to the
grader (artifacts, README, replay), and to the league (conformance kit).

**Audience:** the grader (primary); league opponent teams (interop consumers); ourselves (operators
who must run counted series without one irreversible mistake).

## 2. Grade-aligned priorities (effort allocation)

1. **Interop + reliability rail** (never cause a 0/0; pass any audit) — the floor everything
   stands on.
2. **Strategy depth** (belief + planners + tuning) — "the core of the grade" per the binding
   table's own words, and the lecturer's spoken emphasis.
3. **League breadth played early** (counted series vs as many distinct teams as reachable).
4. **The evidence layer** (README report, replay + screenshots, notebook, artifacts).
5. **League infrastructure** (sparring, kit additions) — grade-risk reduction disguised as
   community service.
6. Stretch: arena-judged RL comparison; extra GUI polish.

## 3. Goals, KPIs, acceptance criteria

| Goal | KPI / acceptance |
|---|---|
| G1 Interop correctness | All kit CORE vectors reproduced by our code in CI; M2 oracle spike: full mini-game vs reference peer over public tunnels, mutual audit Verified OK both directions |
| G2 League performance | ≥ `min_games_to_pass` counted series vs distinct teams, clean (pass floor); target: counted series vs every reachable roster team, played early; 0 technical losses caused by us |
| G3 Strategy strength | Arena win-rate vs reference shipped heuristic > 60% per role; champion never loses to previous champion (CI regression gate) |
| G4 Computational fairness | 0 LLM tokens consumed in counted series (template+gazetteer path); no-GPU match posture; signed step-0 every game |
| G5 Rubric compliance | Book App C checklist + guidelines §17/§20 checklists — every item true of the tree at tag time, verified by `scripts/check_submission.py` (written early, kept green) |
| G6 League adoption | Sparring server live before first counted series; kit wire-contract page + audit fixture + pre-match checklist & netcheck script published; ≥ 1 external team certifies against sparring peer |

## 4. Functional requirements

**FR-1 Game engine (book ch.3; every value from the signed config, App F statuses enforced):**
square grid of `grid_size`, orthogonal move/stay only, cop barrier placement (≤ `max_barriers`,
self-or-adjacent cell, truthful public declaration), capture rules (landing + claim, barrier-on-
thief, imprisonment), survival at `max_moves`/`survival_threshold`, scoring table (all six
values), series of `num_games` mini-games, tie rule at `tie_score`. **One rules module, two
orchestration modes:** *referee mode* (single-process, full-information — tests, arena, tuning) and
*peer mode* (hidden positions — live play); no duplicated rules.
**FR-2 Wire contract (reference-mirrored):** MCP tools `negotiate`, `receive_turn`,
`submit_audit`, `receive_control`; `TurnMessage`/`AuditPayload`/`ControlMessage` field sets; turn
token travels with the message.
**FR-3 Crypto layer (kit CORE):** canonical JSON (`sort_keys`, `ensure_ascii=False`, compact
separators), commit `SHA256(canonical(payload)|nonce)`, terms signature, `game_uid`, nonces from
`secrets`, withheld until audit.
**FR-4 Negotiation & constitution:** byte-identical `config/game.json` exchange + signature gate;
**App F validation guard** — the config loader knows each parameter's App F status
(fixed/minimum/negotiable + default) and *refuses to sign or load* any agreement that alters a
fixed value or lowers a minimum (rule 12); per-game config naming + committed per game;
negotiation playbook preference ladder.
**FR-5 Scent & belief:** emission/decay per the cryptographically locked model (kit-pinned
reference form; book-prose divergence documented per the academic-freedom clause); exact Bayesian
belief filter (motion × scent × hint likelihood); per-opponent priors from post-audit profiling.
**FR-6 Strategy seam & brains ⚑:** `BrainBase`-style plugin selected in private TOML; police repo
ships PoliceBrain (expectimax + barrier graph-surgery + claim policy); thief repo ships ThiefBrain
(region-survival maximization + deception timing); baseline brains (random, greedy-Manhattan) in
core for the arena.
**FR-7 Verbal layer:** template hint generation (≤ `hint_max_words` words, `map_area`
landmarks, planner-chosen implied location + committed intent flag); tiered hint parsing
(gazetteer → optional Ollama → optional claude_api); prompt-injection-safe (opponent text never
reaches an LLM with authority or tools).
**FR-8 Reliability rail (book ch.8; App E rules 3–7):** Orchestrator single gateway; strict
state machine with transition table; deadline tracker on every request (`response_timeout_sec`);
watchdog (`watchdog_timeout_sec`) with state persistence + controlled shutdown; chaos-drill harness
proving each pattern with committed evidence.
**FR-9 Reporting rail (book ch.9/App A; App E rules 28–34, 51–54):** four artifacts
(declaration/config/log/result) named by `game_uid`; step-0 declaration (hardware, model, tokens,
commit hash) signed; Gmail API send-only OAuth, **draft-mode default + human arming interlock**;
gatekeeper (token-bucket + quota manager + DoS detector). **Config precedence:** the binding
gatekeeper minimums live in the signed `game.json` `rate_limiter_gatekeeper` block (App F table
19); the per-peer operational file `rate_limits.json` (guidelines §5.2 / reference layout) may
only **meet or exceed** them — shared-signed values win on any conflict, same overlay rule as the
rest of the constitution.
**FR-10 GUI & replay (book ch.7; App E rules 8–9, 20):** live local-truth view (belief heatmap +
turn banner; never the objective board); replay viewer re-verifying every step → Verified OK /
TAMPERED; **belief-vs-truth overlay** + belief-error curve (post-audit data only).
**FR-11 Audit extensions:** standard mutual re-hash audit; **scent-physics consistency check**
(re-derive opponent's expected trail from revealed moves + locked model vs the grids they
transmitted) — evidence-grade logging on mismatch.
**FR-12 Arena & tuning:** headless seeded tournament harness over referee mode; genetic weight
tuning via self-play; fitness/learning curves + parameter sensitivity analysis exported to the
results notebook and README.
**FR-13 Series operations:** series runner (`num_games` mini-games, per-game config/roles);
sparring mode (both roles, generic brain, always-on host); friendly mode (reports never leave
draft); game-count declaration per rules 37–38.
**FR-14 SDK layer (guidelines §4):** all business logic behind a single SDK entry point consumed
by CLI, GUI, arena, sparring runner, and series runner alike.

## 5. Non-functional requirements

- **Quality gates (guidelines V3 + HW6 tightenings, never loosened):** files ≤ 150 code lines;
  ruff 0 violations (E,F,W,I,N,UP,B,C4,SIM + ANN,RET,PT); coverage ≥ 85% global / ≥ 90%
  deterministic core with CI `fail_under`; `mypy --strict` clean on `src/`; TDD red→green→refactor;
  OOP/DRY extraction rules; building-block docstrings (Input/Output/Setup); `__init__.py` exports
  with `__all__` + `__version__`; versions start 1.00, validated at startup.
- **Config ownership:** zero quantitative values in code; all values from the signed `game.json` /
  private `game.toml` / `rate_limits.json` per the overlay rules; `constants.py` holds only
  physical/mathematical constants; a `check_no_hardcoded`-style scanner enforces it.
- **Security:** no secrets/OAuth artifacts in repos (`.gitignore` + `.env-example`); send-only
  Gmail scope; MCP inputs validated before use; opponent data treated as adversarial.
- **Keyless CI:** mock LLM, in-process MCP fake, no network or live services; kit CORE vectors run
  every pass; both repos' CI verify the core-mirror manifest hash.
- **Performance:** move decision ≪ `response_timeout_sec` on modest hardware (pure-Python filter
  on a `grid_size`² board); no GPU required at match time.
- **Concurrency safety:** processes for role separation (mandated); threads only in
  watchdog/inboxes with locks/queues (guidelines §15).
- **Observability:** structured JSONL logs with provenance; every counted-series artifact
  reproducible from logs + declared commit hash.

## 6. Assumptions, dependencies, constraints, out-of-scope

**Assumptions:** reference peer runnable as oracle (M2 verifies; fallback = self-play across two
machines + kit vectors); league roster materializes (mitigation: sparring + early outreach);
NotebookLM answers advisory only — verified against code/table before load-bearing use.
**Dependencies:** FastMCP; uv; named tunnel (Cloudflare/ngrok); Gmail API (App A flow); small
always-on host for sparring; Ollama optional (dev-time).
**Constraints:** book + App F only truth; EULA respected (private repos, interface-mirror,
micro-snippets attributed); HW6 frozen (mine only); no email without Imree's explicit per-send OK;
nothing announced to the league unless true of the tree.
**Out of scope:** RL as decision foundation (arena-judged experiment at most); relay/central game
services; A2A/ACP; public impl repos during the season; LLM-decided moves (absent a future
documented mutual-consent agreement — not planned).

## 7. Timeline & milestones (deadline > 1 month; counted series played EARLY)

M0 process bedrock → M1 walking skeleton (engine + crypto + wire, localhost) → **M2 oracle spike =
go/no-go gate** (+ SQ1 scent-emission timing, SQ2 capture-claim semantics, SQ3 smell-grid sealing)
→ M3 perception (scent, filter, parser, templates, baselines, arena) → M4 observability (GUI,
replay, overlay) → M5 intelligence (planners, genetic tuning, profiling) → M6 reporting rail →
M7 league ops (sparring → kit additions → friendlies → counted series) → M8 submission hardening.
Every milestone has a binary observed-end-to-end exit criterion (defined in PLAN); per-mechanism
PRDs precede their milestone's code.

## 8. Deliverables & README structure

Each repo ships: `README.md` = the academic report (book §9.4.2 mandatory sections: Dec-POMDP
formal model · FastMCP orchestration dilemmas incl. our documented book-contradiction choices ·
strategies implemented · learning/fitness curves · **screenshots: live belief heatmap + replay
Verified OK** · sibling link) **plus** the guidelines user-manual sections (install, usage, config
guide, contribution, license) · `docs/` (PRD, PLAN, TODO, per-mechanism PRDs, ADRs, PROMPTS.md) ·
`config/` (game.json per game, game.toml, rate_limits.json) · results notebook
(`notebooks/results_analysis.ipynb`: arena + sensitivity + cost) · honest-disclosure triad
(`KNOWN_LIMITATIONS.md`, `SELF_GRADE.md`, `COST.md`) · four per-game artifacts · annotated
`v1.0-submission` tag. `scripts/check_submission.py` = the living submission checklist (App C
table 6 + guidelines §17), written early, run in CI.

## 9. ADR ledger (initial)

ADR-0001 mirror + sync-check topology (police lead) · ADR-0002 interface-mirror + reference-as-
oracle (EULA posture, micro-snippet attributions) · ADR-0003 crypto-before-cloud build-order
deviation from the book's stage 6 · ADR-0004 scent model: kit-pinned reference form vs book prose
(academic-freedom documentation) · ADR-0005 strategy track: belief+search over RL (arena evidence
attached when available) · ADR-0006 deploy split: matches from operator machine + named tunnel;
sparring on always-on host · ADR-0007 zero-token verbal layer (template + gazetteer; injection
defense). More as decisions arise; format: Context / Decision / Status / Consequences /
Alternatives.

## 10. Risk register (top; full tracking in TODO)

| Risk | Sev | Mitigation |
|---|---|---|
| Opponent-caused 0/0 (their crash/drift zeroes us) | High | Kit certification + sparring + friendlies before the counted series; most-reliable opponents first |
| Wire-contract misread (tool names/fields/sequence) | High | M2 oracle spike gates everything; contract mirrored from running code, not docs |
| Canonicalization drift at audit (`ensure_ascii`, float repr, state string) | High | Kit CORE vectors in CI from day one; cross-audit in every friendly |
| Accidental real send burns a counted slot | High | Draft-mode default + destination from signed agreement + human arming step (mechanical, not vigilance) |
| Reference peer not runnable as oracle | Med | Fallback: self-play across two machines + kit vectors; escalate wire questions via NotebookLM→code verification |
| League roster too small / late | Med | Sparring server + early outreach (Alon first); the pass floor needs only `min_games_to_pass` series |
| Unpublished fairness formula penalizes unknown inputs | Low | Dominate every measurable input: 0 tokens, no GPU, modest declaration |
| Genetic tuning overfits self-play | Med | Arena includes reference-heuristic + baseline brains as out-of-population opponents |

## 11. Self-grade categories (rule 55: **code quality only — never league results**)

Architecture & orchestration patterns · protocol/crypto correctness & interop evidence ·
strategy-module engineering (clarity, tests, tuning methodology — not win-rate) · reliability
engineering (state machine, deadline, watchdog, chaos evidence) · documentation & research
artifacts · process discipline. Runnable `self_grade.py`; conservative calibration (target 92–93,
cap 95); `SELF_GRADE.md` prose == script output.

## 12. Team & ownership

| Name | GitHub | Role |
|---|---|---|
| Imree Cohen | @Imreec | Driver/terminal, integration, publishing, all sends |
| Eyal Shtinmetz | @eyalsht | Review, per-task ownership (async) |

Honest representation per `git shortlog`; branch → PR → cross-model review → squash-merge; never
push to `main`. *(Team composition + the 8-char group ID to be confirmed — open item OI-1.)*

## 13. Open items (resolve in-build; not gate blockers)

- **OI-1:** confirm team composition for the final project + register the 8-char group ID.
- **OI-2:** M2 spike questions SQ1–SQ3 (scent timing · capture-claim semantics · smell-grid
  sealing) — answered against the running reference, then folded into PRD_belief / PRD_audit.
- **OI-3:** named-tunnel provider choice (Cloudflare named vs ngrok reserved) — decided at the M2
  spike with a one-line ADR note.
- **OI-4:** sparring host pick (Render free tier vs small VPS) — decided when M7 nears; render.yaml
  know-how ports either way.
- **OI-5:** exact Gmail OAuth project/consent setup per App A — verified against HW6's working flow
  at M6.
- **OI-6:** whether the kit gains the wire-contract page before or after the first friendly —
  sequenced by M2 outcome.

## 14. Role deltas ⚑ (how the two repos' PRDs differ)

Police repo: FR-6 = PoliceBrain (barrier scheduling, capture-claim policy); README narrates
pursuit/partition strategy; lead repo for core development. Thief repo: FR-6 = ThiefBrain
(survival, articulation-point awareness, deception timing); README narrates evasion/deception;
core arrives via sync commits. All other text identical (mirror-checked).
