# M7-21 — Retuning the thief now that it is informed (claim-channel follow-up)

> ⚑ Thief repo. Closes the follow-up M7-18 opened: M7-16 evolved our book-v1 thief vector
> under a **hidden** feed, and M7-18 then taught the thief to read the opponent cop's
> capture claims — so the deployed weights were tuned for a blinder agent than we field.
> **Result: the retuned vector WINS both gates and is DEPLOYED on the book-v1 overlay.**
> Generated instruments: `m7-21-ga-informed.md`, `m7-21-gate-bookv1.md`,
> `m7-21-gate-reference.md`. Contrast with the cop-side attempt (`m7-20-*` in the police
> repo), which failed its gate and did not ship.

## 1. Diagnose before spending the run

The cop-side M7-20 run burned a full GA on a pool that could not resolve its own candidates.
Applying that lesson **before** running anything here, per-member spread across four
deliberately spread-out thief vectors (default / deployed / genes-low / genes-high), 32 seeds:

| cop world | thief blind (how M7-16 tuned) | thief reading claims |
|---|---|---|
| ref-police (0.15 barriers) | 0.438 | 0.250 |
| ref-police (no barriers) | 0.375 | **0.562** |
| greedy chaser | 0.375 | **0.562** |
| random | 0.094 | 0.000 |

This pool **discriminates** — unlike the cop's, where the claim policy flattened the only
informative member. It also showed the headroom directly: against two of the three real cop
worlds a probe vector reached **1.000** survival while the deployed vector sat at 0.656. That
is what justified spending the run.

## 2. What the GA found, and why it makes sense

Fitness (mean survival across the pool, seeds 401–432): **0.602 → 0.805**.

| gene | M7-16 deployed | M7-21 evolved |
|---|---|---|
| `w_articulation` | **40.0** (box ceiling) | **8.93** |
| `w_distance` | 3.60 | 4.56 |
| `ramp_multiplier` | 2.48 | 3.55 |
| `ramp_start_fraction` | 0.3 (floor) | 0.3 (floor) |

**The headline is `w_articulation` collapsing from the ceiling.** That gene is the
anti-cornering machinery — expensive reasoning about whether a region is a trap. It was
carrying a *blind* evader that had to infer danger. An informed evader does not need to
infer: it knows which cell the cop occupies, and is better off simply keeping distance.
Selection found the same thing the M7-19 sweep found on the cop side — information changes
which heuristics earn their keep.

Note the evolved `w_articulation` (8.93) lands close to the **base** reference-tuned table's
8.16, which was itself evolved in a world where the thief could not see the cop but the
physics made the scent trail informative. Two different routes to "don't over-think it".

## 3. The gate says yes — in both physics

Held-out seeds 1–32, disjoint from the GA's 401–432. Both thief candidates read claims
(what M7-18 deployed), against a **mixture** of cop worlds including a **quiet** cop
(`claim_threshold = 2.0`) against whom claim-reading buys nothing.

**Counted physics (`multiplicative_book_v1`):**

| thief | points | survivals |
|---|---|---|
| `thief-m7-21` | **1260** | **124** / 128 |
| `thief-champion` (M7-16) | 1170 | 106 / 128 |

Better **or equal on every arm**: ref-police 30 v 21, greedy-loud 30 v 21, random 32 v 32,
greedy-quiet 32 v 32. No arm regresses.

**Reference physics (the no-regression half):**

| thief | points |
|---|---|
| `thief-base-deployed` (the BASE table) | **950** |
| `thief-m7-21` | **950** |
| `thief-champion` (M7-16) | 925 |

The new vector **ties** the base table and beats the previous overlay.

## 4. Deployment: the overlay only

`[strategy.thief.multiplicative_book_v1]` in `game.toml` (v1.02). **The base table is
untouched** — under reference physics the new vector only ties it, which is no reason to
change what already plays there. Same posture as M7-16.

Adding the base vector to the reference gate was a deliberate correction mid-run: without
it, that gate compared two book-v1 vectors under reference physics and could not answer
"should the base change too?". It can now, and the answer is no.

**Live peer-path validation:** overlay resolves (`w_articulation` 8.93 under book-v1, 8.16
under the shipped default); full local mini-game → `thief_survival` 35 steps, **mutual
audits OK both sides**, replay **Verified OK, 71 records**.

## 5. What is NOT claimed

- Four modelled cop worlds are not the league. They bracket a threat class.
- The gain is **conditional on the thief actually being informed**, which in turn depends on
  the opposing cop declaring. Against the `greedy-quiet` arm both vectors survive 32/32, so
  nothing regresses there — but nothing is won there either.
- The pool models a quiet cop **conservatively**: claims are not modelled on the capture
  side, so every same-cell ending still resolves and the quiet cop is treated as being as
  dangerous as a loud one. That understates our survival rather than flattering it.
- Book-v1 only for the overlay. The base table's world is unmeasured by the GA here.
- No cop weights are touched by this milestone, in either repo.

## 6. Follow-up

The symmetry is now uncomfortable and worth stating: our thief gains a lot from reading
claims, and our cop deployed a policy to deny exactly that to opponents. If opponents adopt
the same policy, this vector's advantage narrows toward the `greedy-quiet` column — where it
ties rather than wins. That is the arms race the claim channel opens, and it argues for
keeping the mixture (informed **and** uninformed worlds) in every future thief retune rather
than tuning against a fully-informed world.
