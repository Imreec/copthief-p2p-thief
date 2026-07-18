# M3 full-pairing friendly — our THIEF vs the reference COP (2026-07-18)

> The pairing deferred at M2: the reference cop places barriers, and until M3-3 our
> peer ignored inbound `barrier_placed` (spike finding F9 — the M2 g2 evidence was
> legitimate only by luck). With F9 merged (police PR #18 → both mains), Imree
> authorized this run. One keyless friendly over the public tunnels — draft-tier,
> no league reporting, nothing announced.

## Setup

| Item | Value |
|---|---|
| Reference | `FinalProject\reference\Game-P2P-Cop-Chase`, pinned sha `960499fd` (v3.0.0), role police :8802 behind `cop.imreeyal.com` |
| Us | this repo @ main `16d526f` (post-M3 sync), role thief :8801 behind `thief.imreeyal.com` |
| Keyless posture | Ours: template hints (gazetteer composer), no LLM path. Theirs: `--stub-llm`, template provider, email disabled. 0 tokens both sides |
| Command (ours) | `uv run copthief run peer --role thief --seed 22 --port 8801 --opponent-url https://cop.imreeyal.com/mcp --log docs/evidence/m3-full-pairing-g1.jsonl` |
| Command (theirs) | `uv run python -m police_thief peer --role police --stub-llm --no-gui` |

## Result

| Check | Observed |
|---|---|
| Outcome | `thief_survival`, 35 steps (34 their count — the known one-turn-short asymmetry, mirrored: this time THEY end short on OUR win claim) |
| Shared game_uid | `deee14f6-a464-b861-c2e9-bd49d3f0926e` — derived identically both sides |
| Our audit of theirs | **Verified OK** (`audit_ok: true`, `problems: []`) |
| Their audit of ours | **passed, 35/35 steps verified, failed_steps []** |
| Mutual agreement | `mutual_agreement.confirmed = true` in their result artifact |
| Tokens | 0 both sides |

## F9 closure observed live (the point of the run)

The reference cop placed **7 barriers** during the game. Post-game analysis of our
own sealed records (each state string carries the barrier set known at sealing time):

- Barrier knowledge grew step-by-step in our records: 0 → 1 (step 3) → … → 7
  (step 30) — inbound `barrier_placed` is being noted into our board, live.
- **Zero violations:** our thief's sealed position was never a known barrier cell,
  at any step. At M2 the same property held only by luck (verified path analysis);
  now it holds by construction — `legal_moves` excludes declared barriers, and the
  belief motion model diffuses around them.
- Our hints all came from the gazetteer composer (closed-vocabulary round-trip),
  and all 35 turns transmitted a locked-model trail with exactly one 0.8 fresh
  center — scent + hints + barriers all live against the reference in one game.

## Residual note (honest)

Same limitation as the cop-side friendly: inbound message bytes are not archived in
our JSONL (their grids/barrier declarations are consumed live and provable only via
our sealed-record side-effects); inbound-verbatim logging is scoped to M4
observability. Reference-side artifacts stay in the reference checkout (ADR-0002).

## Artifacts

- `docs/evidence/m3-full-pairing-g1.jsonl` — our full outbound log (negotiated + 35
  turns + audit + peer_result).
- Reference verdict quoted from its `logs/police_match.json` and
  `logs/segal-police-team/result_imreeyal-vs-segal-police-team.json`.
