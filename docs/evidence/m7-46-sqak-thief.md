# M7-46 — why uoh-sqak's cop took all three thief sub-games, and what fixed it

> Source of the loss: the 2026-08-07 friendly `imreeyal-vs-uoh-sqak`, sub-games g02, g04,
> g06 (we played thief in all three). Wire logs: `logs/imreeyal-vs-uoh-sqak_g0{2,4,6}.jsonl`
> in the police repo. Their agent is public: <https://github.com/salah-dev-stu/uoh-sqak-cop>.
> Everything below is reproducible offline — no opponent, no window, no network.

## 1. What the wire shows

All three sub-games are **byte-identical**. Their cop played the same thirteen barriers in
the same order and our thief played the same fifteen moves, ending `cop_capture` at step
14 in each:

| | |
|---|---|
| their barriers | `(0,1) (0,0) (1,0) (2,0) (3,0) (4,0) (4,1) (5,1) (4,3) (3,1) (2,1) (0,2) — (1,5)` |
| our path | `(3,4) (3,5) (4,5) (4,6) (5,6) (6,6) (5,6) (4,6) (3,6) (2,6) (1,6) (0,6) (0,5) (1,5) STAY` |
| their cop | `(1,0) (2,0) (3,0) (4,0) (5,0) (5,1) (5,2) (4,2) (3,2) (2,2) (1,2) (1,3) (1,4) (0,4)` |
| ending | barrier dropped on our cell at (1,5) — App E rule 46 |

Their cop cell each step is read off the scent peak of every `turn_received`: our agreed
field puts a unique `emit − decay = 0.8` stamp on the sender's exact cell.

## 2. Their brain, from their source

`config/police/game.toml` fields `apex_cop:ApexCop`, a three-layer pursuer:

- **L1** `ScentDecoder.fresh_peak` — our field's unique 0.8 peak IS our cell, so their
  belief on us is **exact, every turn**. Nothing we do with deception reaches this cop.
- **L2** best-response: pick the (step, wall) minimising the thief's *escape value*
  `1.0·reachable_area + 0.6·gap + 0.8·wall_distance` over an ensemble of three predicted
  thief replies. Area dominates (it reaches 49 where the others reach single digits), so
  L2 is an area-strangler.
- **L3** a depth-8 alpha-beta that plays only when it **proves** a forced capture.

A port of all three (`ApexCop` on plain tuples, their fielded weights) reproduces the
friendly **turn for turn, 14 of 14** — every barrier cell and every cop cell — when driven
with our recorded thief path. That validates the port, and with it the premise that their
thief estimate is simply our true cell.

## 3. The correction to the first reading

The first reading of the logs was that our thief *chose to stand still* on (1,5) with all
four neighbours open, and that a stationary thief concentrates its scent and becomes
barrierable. The replica says otherwise: **L3 fired at step 13 and had already proved the
capture** — the `[endgame]` layer takes the last two turns of every lost sub-game. The
STAY at step 15 was a symptom of a position that was lost two plies earlier, not the cause.

The trigger is exact and worth writing down: `wall_distance(thief) ≤ 2 AND gap ≤ 4`,
evaluated only when their belief is locked (which, given L1, is always). Our thief pinned
itself to the east edge from step 4 and never left the trigger zone after step 7.

## 4. The finding that dominates everything else

**Their cop moves AND walls in the same turn.** The wire shows a barrier on 13 of the 14
turns while their cop walked (0,0) → (0,4); their `peer/turn_sender.py` applies
`moved_to(target)` unconditionally alongside `barrier_placed`.

The book's named **Barrier Law** (ch.3, stated twice) is explicit:

> בתור שבו השוטר **מוותר על תנועה** הוא רשאי להציב מחסום בכל תא שבמרחק צעד אחד ממנו
> — *in a turn in which the cop **forgoes movement**, he may place a barrier in any cell
> within one step of him — the cell he stands on or one of the four orthogonal neighbours.*

Our engine implements that reading (`Decision` is move XOR barrier, ADR-0002). Theirs does
not, and their docs record no deliberate divergence, so this reads as an unnoticed gap
rather than an academic-freedom choice. A second, smaller deviation rides along: they test
barrier adjacency against the **pre-move** cop cell and then move anyway, which is how the
killing wall at (1,5) was placed from (1,4) by a cop that ended the turn at (0,4), two
cells away.

**This is worth more than the strategy fix.** Measured on the replica, over the 32-scenario
suite:

| cop turn law | pre-M7-46 thief | shipped thief |
|---|---|---|
| their tempo, L2 + endgame | **0 / 32** survivals | 10 / 32 |
| their tempo, L2 only | 1 / 32 | 15 / 32 |
| **our tempo (the book's), L2 only** | **32 / 32** (0 captures in 64 games) | 32 / 32 |

The endgame layer is worth about one game in thirty-two. **The tempo is worth all of them.**
Their policy under the legal turn law captures nothing at all
(`docs/evidence/m7-46-sqak-arena.md`). This is a league question for Imree, not something
this repo settles on its own; it is raised here with the measurement attached.

## 5. The fix — siege-conditional support width

Our flight vector averages the distance to the `top_k = 4` most likely cop cells. Against a
pursuer we localise loosely that hedge is right; against one that walls every turn it is
wrong, because a siege closes the gap faster than a smeared support lets us flee. Our
belief argmax was **correct on 12 of the 14 steps** — the mass just decayed from 0.80 to
0.12 and smeared across 37 cells, so the hedge fled a cloud instead of the cop.

Two things were tried and rejected first, both measured, both kept as negative results:

- **`top_k: 4 → 1` unconditionally.** Beats uoh-sqak (0/16 → 8/16) and **regresses every
  existing arm** — 32 → 26 survivals vs `greedy-manhattan`, 27 → 22 vs `ref-police`
  (`docs/evidence/m7-46-topk-arena.md`). Fails the CLAUDE.md §5 gate. Not shipped.
- **A centrality term** (`w_center · wall_distance`, aimed straight at their L3 trigger).
  0/16 at every weight from 1.0 to 12.0 — staying central just lets them close the gap,
  which is the other half of their objective. Not shipped.

What shipped is `features.support_width`: the wall **rate** is observable from our own
board (barriers are declared and sealed, so the count is certain), and the support narrows
to `siege_top_k = 1` only once the opponent has proved itself a sieger —
`siege_min_walls = 2` walls placed **and** `siege_wall_rate = 0.5` walls per elapsed step.

Against uoh-sqak's live tempo, 32 scenarios: **0/32 → 10/32 survivals**, mean steps
10.9 → 19.9, and the **signed start** — the one every counted game plays — flips from
`cop_capture` at step 14 to `thief_survival` at 35. That is a 20-point swing per sub-game.

## 6. The gate

`greedy-manhattan` and `random` never wall, and `ref-police` walls at 0.15, so the siege
condition never fires against the shipped roster — by construction, and confirmed by
measurement. The CI-gated arena is **byte-identical** to its pre-change state:

| brain | role | games | wins | points |
|---|---|---|---|---|
| greedy-manhattan | thief | 24 | 21 | 225 |
| thief-brain | thief | 24 | 21 | 225 |
| ref-thief | thief | 24 | 20 | 220 |
| random | thief | 24 | 6 | 150 |

Per-arm survivals unchanged: 8/8 vs `random`, 8/8 vs `greedy-manhattan`, 5/8 vs
`ref-police`. DoD 27/32 = 84% (floor 60%). **Regression gate GREEN**, no arm replaced.

## 7. Reproduce

```
uv run pytest tests/role/test_sqak_live_tempo.py    # the loss and the fix, pinned
uv run pytest tests/role/test_thief_siege.py tests/role/test_sqak_apex.py
uv run python scripts/arena_run.py                                     # the gated arena
uv run python scripts/arena_run.py --config config/arena_m7_46_sqak.json
uv run python scripts/arena_run.py --config config/arena_m7_46_topk.json
```

## 8. What is still open

- The move-and-wall question above — **Imree's call**, and it cuts both ways: if the
  reading is legal, our own cop is forgoing half its tempo in every counted game.
- Our belief filter is strictly weaker than theirs on identical evidence: their
  `fresh_peak` reads the sender's exact cell off the unique 0.8 stamp, while our
  `age_voucher` path smears to 0.12 mass over 37 cells. Sharpening it is a
  `copthief_core` change and therefore a **police-repo** edit (CLAUDE.md #14), not
  something this repo may make.
- `SqakApexPoliceBrain` omits their L3 endgame layer, which cannot be expressed under a
  move-XOR-wall turn law. A survival against that arm is **not** a survival against them.
