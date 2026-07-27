# M7-18 — What reading capture claims is worth to the DEPLOYED thief (claim channel, half 1)

> ⚑ The thief repo's half of M7-18. The core change arrived by sync from
> `police@338fe39`; the cop repo's analysis is `docs/evidence/m7-18-claim-channel.md` there.
> This document answers the one question that repo could not: its configured thief is
> `random`, so the number for the vector **we actually ship** had to be taken here.
> Generated instruments: `m7-18-claim-channel-arena.md`, `m7-18-claim-tracking.md`. Both
> regenerate deterministically from committed configs by the commands in their headers.

## 1. The question

M7-16 retuned and deployed our book-v1 thief vector, and disclosed a hard number: against
the belief-driven chasers it survived only **8 of 32** under `multiplicative_book_v1`. The
cop repo's M7-13 postmortem had already named why that mattered — the opponent's cop
announces its landing cell on every moving turn, and we were throwing that away.

The core now reads those claims. Did the gap close?

## 2. Peer path — tracking the cop with the brains we ship

`scripts/claim_probe.py`, this repo's configured brains, 16 games, `multiplicative_book_v1`,
identical parameters on both sides:

| | exact cop-tracking at decision time |
|---|---|
| before (pre-sync core) | 273/544 = **0.502** |
| after | 541/544 = **0.994** |

Our thief used to be right about the cop's cell on barely half its decisions. It is now
right on essentially all of them.

## 3. Arena — does that convert into survival?

`config/arena_m7_18.json`: the **same deployed vector**, same options, run twice — once on
the hidden feed, once reading claims. Only the information differs. Survivals of 32 under
`multiplicative_book_v1`:

| police brain | `thief-brain-bookv1` (hidden) | `thief-brain-claim` (reads claims) | Δ |
|---|---|---|---|
| `random` | 32 | 32 | 0 |
| `greedy-manhattan` | 8 | **21** | **+13** |
| `ref-police` | 13 | **21** | +8 |
| `ref-police-chaser` | 8 | **21** | **+13** |
| **wins / points** | 61 of 128 · 945 | **95 of 128 · 1115** | +34 wins · **+18.0%** |

**The M7-16 gap closed by most of its width.** Against both chasers — the arm that produced
the 8/32 warning — survival goes 8 → 21 of 32. Against a random cop nothing changes, which
is the right null result: there is no pursuit to evade and no information worth having.

**Cross-check that the A/B is controlled:** the hidden column reproduces the committed
M7-16 table cell-for-cell (32 / 8 / 13 / 8). The only thing that changed between the two
columns is the feed.

## 4. What this does and does not claim

- It measures **our** thief against **modelled** cops. The opponent's real cop is not in
  this roster, and his thief's behaviour is not what is being measured here at all.
- The gain is contingent on the opposing cop actually announcing. Every cop in this roster
  does, because the reference does and both teams mirrored it. **An opponent who adopts a
  quiet-cop policy takes this back** — which is precisely the other half of the channel
  (M7-19, cop repo), and the reason the two halves were specified together.
- The arena arm uses the `truth` feed, which is very slightly optimistic: it grants
  certainty even on the cop's silent turns, where a real claim-reader gets none. §2's 0.994
  is the honest figure and sits just below it — under book-v1 the honest scent holds the
  argmax through most silent turns, so the bracket is narrow here.
- Nothing in this milestone changes a single strategy weight. The improvement is
  information, not tuning.

## 5. Follow-up this measurement opens

Our thief's GA pool tuned it against cops under a **hidden** feed. Now that the thief is
informed, its evolved parameters — an anti-camping ramp tuned for a thief that did not know
where the cop was — may no longer be the right shape. Worth a retune against the informed
world, and named here rather than done silently, because it changes deployed weights.

The symmetric point on the cop side is already recorded there: the cop's book-v1 pool used
a `truth-lag1` arm that understates a real claim-reader, and should retune against lag 0.
