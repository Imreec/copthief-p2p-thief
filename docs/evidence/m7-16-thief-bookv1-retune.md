# M7-16 — The thief's book-v1 retune: anti-camping emerges from selection

**2026-07-26, the thief half of the counted-series strategy prep (cop-side record:
the police repo's `docs/evidence/m7-14-bookv1-strategy.md` and
`m7-15-mixed-retune.md`; this repo received the machinery via sync #49). Everything
below regenerates deterministically from committed configs.**

## 1. Why this was urgent

The M7-13 capture postmortem (police repo) found our thief camps HARDER than the
opponent's (STAY streaks up to 14 in the friendly) and survived only because their
cop never converted the resulting scent beacon. The M7-14 belief fix showed what a
beacon-converting cop looks like: under `multiplicative_book_v1` with the
kernel-innovation belief, the plain argmax chaser became the strongest measured cop.
Probed here before tuning: **the deployed (reference-tuned) thief survives only 5/16
against that chaser under book-v1.** The camping habit was unpriced risk; this
retune prices it.

## 2. The retune (`config/ga_bookv1.json` → `m7-16-ga-bookv1.md`)

Mixed-opponent pool (the M7-15 mechanism): ref-police with walls (0.15), ref-police
as a pure chaser (0.0), greedy-manhattan, and a random walker — all under the
pair-locked book physics, fitness seeds 401–416 (disjoint from the DoD seeds 1–32
and the reference-GA seeds 201–248). Mean survival: **0.391 → 0.609**.

The evolved vector is the postmortem's prescription emerging from selection
pressure, not from hand-tuning:

| knob | reference-tuned (deployed base) | book-v1-evolved |
|---|---|---|
| ramp_start_fraction | 0.9496 | **0.3 (box floor)** |
| w_articulation | 8.1599 | **40.0 (box ceiling)** |
| w_spread | 1.0655 | **2.0 (box ceiling)** |
| trap_size_fraction | 0.2945 | 0.1581 |
| w_distance | 5.2704 | 3.6023 |
| w_region | 1.8097 | 2.2014 |
| ramp_multiplier | 1.3136 | 2.4797 |

`ramp_start_fraction` is the headline: the reference-tuned thief only begins hard
evasion at ~95% of the clock — i.e., it CAMPS for most of the game, exactly the
g02-losing pattern — while the book-v1 world pushes it to the box floor: evade from
30% of the clock. Maxed articulation-avoidance and spread are the trap-awareness
and keep-options terms.

## 3. The gate (four cops × four thieves, 32 seeds, both physics)

Survivals /32 for the two tuned thieves, under `multiplicative_book_v1`
(`m7-16-bookv1-arena.md`):

| vs cop | thief-brain (old) | thief-brain-bookv1 (new) |
|---|---|---|
| greedy-manhattan | 3 | **8** |
| ref-police-chaser (0.0 walls) | 3 | **8** |
| ref-police (0.15 walls) | 11 | **13** |
| random | 32 | 32 |

Role-table points: **new 945 (61 wins) > ref-thief 900 > old 885 (49 wins)** — the
retuned thief tops the book-v1 table; the old vector had fallen behind even the
reference heuristic there. Under reference physics (`m7-16-reference-arena.md`) the
old vector keeps its crown (123 wins / 1255 vs new 107 / 1175) — the same
physics-specificity the cop side measured, resolved the same way:

## 4. Deployment

The evolved vector rides `game.toml [strategy.thief.multiplicative_book_v1]` (the
M7-15 overlay mechanism, arrived via sync #49); the base `[strategy.thief]` table
keeps the proven reference vector. Live-validated on the peer path from a
scratchpad config copy: the overlay resolves under book-v1, a full local mini-game
plays to survival with clean mutual audits and a Verified-OK replay, and the
shipped default config still resolves the base vector untouched.

Candid limits: the cop pool is core-name heuristics — the opponent's actual cop is
his own build, so these numbers bracket a threat class, not his implementation; and
the book-v1 world remains cop-favored at these arms (best cops still win ~75% of
games against the retuned thief on varied starts — the signed canonical start,
scenario #1, is friendlier to the thief than the suite average).

## Reproduction

```
uv run python scripts/ga_run.py    --config config/ga_bookv1.json
uv run python scripts/arena_run.py --config config/arena_bookv1.json
uv run python scripts/arena_run.py --config config/arena_evaders_reference.json
```
