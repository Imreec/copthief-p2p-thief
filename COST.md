# COST.md — computational-fairness ledger (thief agent)

> Honest-disclosure triad (CLAUDE.md §7), M6-8. **Every number here is true of the tree at
> this commit** — claims are backed by committed evidence and permanent CI pins, never by
> assertion. Sibling: [copthief-p2p-cop](https://github.com/Imreec/copthief-p2p-cop) (lead).

## 1. The headline: 0 LLM tokens at match time, doubly proven

The verbal layer is the zero-token template + gazetteer path (ADR-0007): moves are pure
Python (App E rule 25), hints come from the closed-vocabulary composer, and no LLM is
invoked anywhere in a game. The claim carries **two independent proofs**:

1. **The event log.** Every game's JSONL records each decision; every committed evidence
   log reports `0 tokens` (this repo's M3 full-pairing friendly `docs/evidence/
   m3-full-pairing.md`; the cop-side M2 Stage A g1–g4 and M5 friendly g1–g3).
2. **The sealed per-step counts (M6-3) — cryptographically auditable.** Since M6-3 every
   sealed record carries `model`, `tokens_step`, `tokens_total` INSIDE the commit-reveal
   payload: the counts are hash-bound at the moment of play, revealed at audit, and
   re-verified by replay. A forged count flips the match to TAMPERED (rule-19 mutation
   matrix covers the token fields). Permanent CI pin (mirrored):
   `tests/integration/test_zero_tokens.py` — a real audited game in which every sealed
   game record charges 0/0 and the log replays **Verified OK**.

The step-0 declaration seals `model` per game and the whole-series declaration reports
`סך_טוקנים_שנצרכו` / `tokens_total_series` = 0 from the same sealed source (M6-2/M6-3).

## 2. Match-time posture (G4, App E fairness)

| Input | Value | Evidence |
|---|---|---|
| LLM tokens per counted series | 0 | §1 double proof |
| LLM model declared at step-0 | `none` | sealed `model` field; `game.toml [game] llm_model` |
| GPU at match time | not used | pure-Python belief + search on a `grid_size`² board |
| Hardware declared | probed at step-0 | `shared/sysinfo` (degrades to "unknown", never inflates) |

## 3. Infrastructure costs (operational, not graded inputs)

- **Cloudflare named tunnel** (`copthief` on `imreeyal.com`, shared with the cop): free
  plan; the domain was already owned. No per-request cost.
- **Gmail API** (M6-4 report rail): free; compose-scope OAuth on the dedicated team
  account (OI-5). No billing attached.
- **Sparring VPS (Stage B, OI-4/M7-1)**: planned against the existing GCP trial credits —
  earmarked, not yet spent; this table updates when it deploys.

## 4. Development-time disclosure

Development used AI coding tools (Claude Code as terminal author; Antigravity as
cross-model PR reviewer) under the process rules in CLAUDE.md §8 — every landed PR is
logged truthfully in `docs/PROMPTS.md` (core changes arrive via the sync ritual from the
lead repo, each sync PR logged). Development tooling consumes tokens on the developers'
side; **none of it touches match-time execution**, which is what the league's
computational-fairness normalization measures (G4).

## 5. Keeping this file honest

Rules: numbers update in the SAME commit as the change that moves them (the doc↔repo gap
is the one fatal failure mode, CLAUDE.md §7); a future non-zero token path (the optional
LLM verbal tier, never planned for counted play) would have to update §1 and ship its own
sealed-count evidence before merging.
