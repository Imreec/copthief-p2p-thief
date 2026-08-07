# M7-47 — the flight ramp should fire on KNOWING, not on the clock

> Opened by a number found while gating M7-46: `best2934-police` — the cop of our other
> counted opponent — captured our thief **14 of 32**. Reproduce with the commands in §6.

## 1. The number, and the correction to it

The first run of this said 23 of 32. That run had the capture-claim channel switched
off, which measures our thief with one of its main sensors disconnected — the exact
error `docs/evidence/m7-45-best2934.md` (police repo) already records as a standing
warning about unmodelled channels. Their `peer_session.capture_claim()` is ungated: if
the role is cop it returns the cell, every turn. Modelled, the honest baseline is:

| | captures | survivals |
|---|---|---|
| `best2934-police` vs our thief | **14 / 32** | 18 / 32 |

which reconciles exactly with the committed 43.8% capture rate in M7-45 (28/64).

## 2. How we were dying

Nine of the fourteen losses had **zero barriers on the board**. We were not being
sealed — we were being run down and caught by co-location, most of them inside eleven
steps. And seed 1 is the **signed start**, the pair every counted sub-game plays: a
capture on step 11.

Their cop is a chaser that only walls at contact (`barrier_engage_range` 1.0, their
fielded value). So this was a pure evasion failure, not a trap-awareness failure.

## 3. Why: the ramp was tuned to a clock, not to knowledge

`survival_ramp` multiplies the distance term once `step ≥ ramp_start_fraction ×
threshold`. The base table ships `0.9496`, i.e. the ramp arms at step 33 of 35 — it
effectively never fires. Our thief ambles for thirty steps and then sprints for two.

M7-16 already found this and moved the overlay to the GA box floor `0.3`. **The base
table was never moved**, and the base table is what we play under the shipped scent
model.

## 4. The obvious fix is a trap, and the gate caught it

Simply arming the ramp early (`ramp_start_fraction` 0.1, `ramp_multiplier` 3.0) scores
**32/32 against best2934** and looks like a clean win in an informed A/B. Deployed to
`game.toml` and run through the CI-gated arena it does this:

| arm | before | after |
|---|---|---|
| `random` | 8 / 8 | 8 / 8 |
| `greedy-manhattan` | 8 / 8 | **0 / 8** |
| `ref-police` | 5 / 8 | **3 / 8** |
| DoD win rate | 84% | **62%** |

`thief-brain` fell from 225 points and a shared first place to 175 and third.

**The regression gate still reported GREEN.** It is pinned to `greedy-manhattan`, and it
only fires when a challenger *tops* a pinned champion — our own brain getting worse is
invisible to it. Worth knowing: on a thief change, the gate's verdict is not sufficient;
the per-arm rows are the actual evidence. (Recorded rather than quietly worked around —
same class as the M7-30 dead-column finding.)

The cause is the informed/uninformed split M7-19 named. The CI arena runs claims-off, so
its cops are *quiet*: the belief stays smeared, and tripling the weight on a distance
computed from a smeared belief makes us sprint confidently in the wrong direction.
Against a **declaring** cop the same ramp is right, because the belief is truth.

Reverted; `game.toml` is untouched by this milestone.

## 5. What shipped: gate the ramp on confidence

`survival_ramp` now takes the mass on the belief's peak and arms on **either** trigger:

- **clock** — unchanged, GA-tuned, same values, same behaviour;
- **belief** — `confidence ≥ sharp_ramp_mass` (0.9) arms `sharp_ramp_multiplier` (3.0).

A separate multiplier on purpose: the clock ramp's value is evidence from a GA run, so
the new behaviour rides on its own knob and fires only on a condition that never held
before. Against a cop we cannot localise the gate stays shut and the brain is
bit-for-bit the one the GA tuned. That is what makes this not the M7-21 mistake again.

Step 1 is excluded (`sharp_ramp_min_step` 2.0). The filter opens as a delta on the
signed start — common knowledge on both sides, not a read on this opponent. Counting it
as one cost a DoD game (84% → 81%) and nothing else; excluding it restored 84% exactly.

## 6. The gate

**Informed world** (`config/arena_m7_47_ramp.json`, 32 seeds, claim channel modelled,
same brain both columns with the gate provably shut on one — `sharp_ramp_mass` 2.0, a
value no probability reaches):

| police arm | sharp ramp OFF | sharp ramp ON |
|---|---|---|
| `random` | 32 / 32 | 32 / 32 |
| `greedy-manhattan` | 32 / 32 | 32 / 32 |
| `ref-police` | 30 / 32 | **32 / 32** |
| `best2934-police` | 18 / 32 | **32 / 32** |
| **points** | 1200 | **1280** |
| **wins** | 112 / 128 | **128 / 128** |

Better or equal on **every** arm, and a perfect card. Nothing is traded for it.

**Uninformed world** — the CI-gated arena (`docs/evidence/m5-arena.md`) is
**byte-identical** to its pre-change state: 8/8 vs `random`, 8/8 vs `greedy-manhattan`,
5/8 vs `ref-police`, 225 points, DoD 27/32 = 84%, gate GREEN. By construction: a quiet
cop never collapses the posterior, so the gate never opens.

**The uoh-sqak matchup (M7-46) is unmoved**: 10/32 at their live tempo, signed start
still `thief_survival` at 35. That was the risk worth checking — the two fixes touch the
same scoring line and neither costs the other anything.

**Signed start, the pair every counted sub-game plays:**

| opponent | before | after |
|---|---|---|
| `best2934-police` | `cop_capture` step 11 | **`thief_survival` step 35** |
| uoh-sqak (live tempo) | `thief_survival` step 35 | `thief_survival` step 35 |

## 7. Reproduce

```
uv run pytest tests/role/test_thief_sharp_ramp.py
uv run python scripts/arena_run.py                                    # gated, unchanged
uv run python scripts/arena_run.py --config config/arena_m7_47_ramp.json
```

## 8. What is still open

- **The ramp knobs were never searched where the answer lives.** `config/ga.json` bounds
  `ramp_start_fraction` to `[0.3, 0.95]`; every value that helps here is below 0.3. The
  GA could not have found this, and did not. The box wants revisiting before the next
  run — a null result from a search that cannot reach the answer is not a null result.
- This milestone changed no GA-tuned weight. `game.toml [strategy.thief]` and the
  `multiplicative_book_v1` overlay are both untouched; the new knobs ship as
  `DEFAULT_OPTIONS` entries.
- The gate blind spot in §4 — the champion pin cannot see our own brain regressing —
  applies to every future thief change, not just this one.
