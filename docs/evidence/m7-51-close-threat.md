# M7-51 — we walked into them with the right answer already in hand

> The 2026-08-08 friendly, lost 5-1 (85-45). Our thief lost g02, g04 and g06 at **exactly
> step 16** each time. Logs: `logs/imreeyal-vs-uoh-sqak_g0{2,4,6}.jsonl` in the police repo.

## 1. They played clean

Checked from the wire, since we had raised the Barrier Law with them the day before:

| | g02 | g04 | g06 |
|---|---|---|---|
| barriers they placed | 0 | 0 | 0 |
| move-and-wall violations | 0 | 0 | 0 |

They honoured `d07b654` completely. Their cop simply chased, and chasing was enough.

## 2. Both of yesterday's fixes sat the game out

- **M7-46 (siege response)** arms on ≥2 walls at ≥0.5/turn. They placed none.
- **M7-47 (informed ramp)** arms on belief mass ≥0.9, which in practice means the cop
  *declared*. Theirs claims only above `claim_mass_threshold` 0.08 — one claim, at the
  capture itself.

Both gates are conditioned on behaviour their fixed cop no longer shows. Neither fired
at any point in any of the three games.

## 3. What actually killed us

g02, step 14. Their message carried this scent field:

```
1,5 → 0.8   1,4 → 0.7   2,4 → 0.6   0,4 → 0.5   0,5 → 0.5
```

`0.8` is `emit − decay` under `subtractive_chebyshev_v1` — the value a just-laid centre
transmits — and it is **unique**. That names their cop's exact cell, (1,5), in plain
text, in a message they sent us. (This is how the whole cop path in §1 was reconstructed.)

Our belief that turn: **argmax (1,5), mass 0.063, spread over all 49 cells.**

The argmax was right. The confidence was not. And with the posterior that flat, the
distance term is nearly equal for every legal move, so the tiebreaker decides — and
`w_spread`, the unvisited-cell bonus, sent our thief **west from (0,6) to (0,5)**, the
cell their cop stepped onto next. We did not fail to see them; we averaged them away.

## 4. The instrument was the real blocker

The M7-46 arm (`copthief_thief/sqak_apex.py`) omits their L3 endgame solver, because it
cannot be expressed under a move-XOR-wall turn law. Measured against it, our thief scores
**64/64 survival** — against a cop that had just beaten us three times out of three. Any
weight tuned on that number would have been tuning to noise.

So the validated scratchpad port was updated to their fixed build first: `_cop_actions`
and `_best_response` rewritten to a step XOR a wall, `min_gain` 1 → 2, `apex_barrier_cost`
0 → 1.0. It now **reproduces the live game 15 of 15 turns**, endgame layer included
(`[endgame]` fires at steps 14 and 15, exactly as it did on the wire), and driven with the
deployed thief it reproduces the capture and the path cell for cell.

Nothing below was tuned until that held.

## 5. What shipped

A second trigger on `features.support_width`: **close threat**.

Far away, which cell the cop occupies barely changes the flight vector, and the `top_k`
hedge against a loosely-localised pursuer is free. Inside `close_threat_distance` (2.0),
the difference between fleeing the argmax and fleeing the average of four candidate cells
is the difference between escaping and stepping into it.

| | before | after |
|---|---|---|
| vs their FIXED cop, 32 scenarios | **0 / 32** | **6 / 32** |
| **signed start** (every counted sub-game) | `cop_capture` @15 | **`thief_survival` @35** |

## 6. The gate

| arm | before | after |
|---|---|---|
| `random` | 8 / 8 | 8 / 8 |
| `greedy-manhattan` | 8 / 8 | 8 / 8 |
| `ref-police` | 5 / 8 | 5 / 8 |
| points | 225 | 225 |
| **DoD win rate** | 27/32 = 84% | **28/32 = 88%** |

Byte-identical on every arm and the DoD *improves*. M7-47 is unmoved: best2934 stays
32/32 with the signed start surviving. Regression gate GREEN, 982 tests.

## 7. Rejected, measured, kept

- **`close_threat_distance` 4.0** — better against uoh-sqak (15/32 rather than 6/32) and
  **fails the gate**: `ref-police` 5/8 → 3/8, DoD 84% → 66%. Not shipped.
- **A fresh-peak belief decoder** — reading their exact cell off the unique 0.8, exactly
  as their `ScentDecoder` does. It works: our tracking of the truth goes **0.063 → 0.98**.
  It also made our **cop catastrophically worse — 45/64 → 0/64** captures against their
  published evader at the signed start, with their decoder held sharp in both columns so
  the comparison was fair. Reverted in the police repo, tests and all.

  That last result is the uncomfortable one and it is not a tuning miss: **accurate is
  not the same as useful** when the consumer is a 2-ply expectimax that, given a
  well-modelled evader, correctly concludes it cannot force a catch and plays passively.
  A fuzzy belief made it blunder forward, and blundering forward worked. Fixing the
  belief therefore needs the search fixed first, and that is a real open problem.

## 8. What is still open

- **We remain nearly blind and they do not.** Their decoder reads our exact cell every
  turn from the same physics; ours sits at 0.063. §7 says we cannot simply close that gap
  without first making our search able to use it.
- 6/32 on varied starts is thin. The signed start is what counted games play, and it
  holds — but this is one deterministic line, not a margin.
- The M7-46 arm still lacks their endgame layer. Numbers from it are upper bounds; the
  scratchpad port is the instrument that tells the truth, and it is not in the tree.

## 9. Reproduce

```
uv run pytest tests/role/test_thief_siege.py
uv run python scripts/arena_run.py
```
