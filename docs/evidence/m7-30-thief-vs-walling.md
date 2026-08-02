# M7-30 — Retuning the thief against walling cops: a NULL RESULT, and the instrument defect that explains it

> ⚑ Thief repo. Opened by the 2026-08-01 warm-up: with M7-29's self-concession live, the
> deployed thief's corner camping became fatal — it sat at (6,6) in s1/s3/s5 and the
> opponent cop sealed (5,6)+(6,5) with 2 of its 14 barriers, identically each time
> (corrected score 45–85 to them).
>
> **Verdict: the retuned vector LOSES the champion gate and is NOT deployed.** No weight
> changed anywhere; `game.toml` is untouched. What this milestone does ship is the reason
> the retune could not work as specified — **the arena has never been able to see the one
> gene meant to prevent exactly this**, plus the sealing threat class the pool never had.
>
> Generated instruments: `m7-30-ga-walling.md`, `m7-30-gate-bookv1.md`,
> `m7-30-gate-reference.md`, `m7-30-gate-articulation.md`. Contrast with `m7-21-*` (the
> retune that shipped) and `m7-20-*` in the police repo (the other null result).

## 1. Probe first — and the probe overturned the premise

The mission was "raise the anti-cornering weight until seals stop killing us". Measuring
before tuning (the M7-20/M7-21 discipline) found that could never have worked.

**(a) The existing pool applies no sealing pressure at all.** Sweeping `ref-police`'s
barrier chance across 0.0/0.15/0.40/0.70/1.00 against four thief vectors, 32 seeds:
the referee resolved **one barrier capture and zero imprisonments in 224 games**. And the
arm *self-neuters* — at a barrier chance of 0.70 or 1.00 our thief survives **32/32**,
because the reference cop walls the cell of the step it would have taken, so every
barrier costs it the advance that would have closed the distance. A GA run over that pool
could not price anti-sealing behaviour at any weight, which is why M7-16 and M7-21 did not.

**(b) `w_articulation` is INERT in the referee — the gene the mission wanted tuned.**
Three values a decade apart (0.0 / the deployed 8.93 / the M7-16 ceiling 40.0) produce
**bit-identical games on every arm**. Root cause, asserted directly rather than inferred:
`strategy/referee_obs.thief_observation` sets neither `barriers_used` nor `max_barriers`,
so `ThiefBrain`'s quota gate reads `0 < 0` and the trap-awareness branch never runs — while
the live peer path fills both (`peer/turns.py`) and so always runs it.

Pinned in-tree by `tests/role/test_referee_articulation_gap.py`, and confirmed at scale by
a 768-game A/B on one gene (`m7-30-gate-articulation.md`): `thief-champion` and
`thief-zeroart` tie **1880–1880** informed, **1655–1655** blind, and every single pairing
row matches.

**The consequence is larger than this milestone.** The M7-16 and M7-21 runs evolved this
gene as free drift — M7-21's own published headline was `w_articulation` "falling from the
box ceiling 40.0 to 8.93", which the arena could not have measured and which nonetheless
changed how the agent plays for real. Every committed thief arena table describes a thief
we do not field.

**(c) No value of the gene could have saved those three sub-games anyway.** From the
signed starts the camp reproduces exactly — 26 of 35 steps at (6,6), longest stay-streak
25 — and the trace is **identical at 0.0, 8.93 and 40.0** even with the instrument
corrected. `min_sealed_component` asks only "does ONE barrier isolate me"; a corner needs
**two**, so the detector is structurally blind to the trap that beat us until the first
gate is already walled, by which point fleeing costs more distance than the penalty is
worth.

**(d) Two candidate fixes for (c), measured and rejected.** A flat penalty on a
destination's open degree (the barrier count needed to seal it) took survivals from
**199/224 to 190/170/168/155** across weightings — it only moved the camp one cell inward.
Making it conditional on the believed cop being close enough to *execute* the seal did no
better: **199/224 → 144–168**. Camping is not the defect; camping is what maximises
distance, and it wins against every cop that never walks over. Recorded so the next
attempt does not re-derive it.

*(a)–(d) were measured in a scratchpad harness that monkeypatches the core observation
builder. **They are not reproducible from this tree** — the core fix is police-lead. What
IS reproducible here: the two pins in (b), the A/B table, and everything in §3 onward.*

## 2. What the milestone adds to the instrument

`copthief_thief/adversary.py` — `SealerPoliceBrain` (chase the belief argmax; wall an
escape gate of a nearly-enclosed believed cell) and, as a disclosed bracket only,
`BarrierCapturePoliceBrain` (also wall the believed cell itself). Both config-gated and
**inert by default**: with no `seal_max_exits` they are plain chasers, so naming one in a
roster changes nothing until a config asks for sealing. 7 TDD pins; never role brains.

These are the first arms in either repo that capture by rules 46–47 rather than by landing.

## 3. The GA run — the pool discriminates, and selection improved it

Per-member spread through the **real** `opponent_fitness`, before spending the run
(M7-20's precondition): spreads **0.094–1.000**, five of six members above 0.28 — far
better resolution than M7-21's pool (0.25–0.56). The headroom was explicit: against the
blind sealer the deployed vector sat at **0.500** where another in-box vector reached
**0.875**. The same table also shows the deployed vector and a zero-articulation copy of it
at an identical **0.781** — (b) again, through the tuner's own eyes.

Pool = the M7-21 mixture **plus** the two sealers, never a replacement. Seeds 401–432.
Fitness **0.615** (defaults) **→ 0.828**; the deployed overlay measures 0.781 on the same pool.

| gene | M7-21 deployed | M7-30 evolved |
|---|---|---|
| `w_region` | 2.030 | **0.028** |
| `w_spread` | 1.784 | **0.000** |
| `w_distance` | 4.562 | 2.946 |
| `ramp_multiplier` | 3.546 | 2.907 |
| `ramp_start_fraction` | 0.300 | 0.344 |
| `w_articulation` | 8.928 | **0.0 (pinned)** |
| `trap_size_fraction` | 0.201 | 0.201 (pinned) |

Two genes were pinned deliberately. `w_articulation` to 0.0 because leaving it free is
exactly what produced the M7-21 drift — the instrument cannot score it, so selection would
emit a number that changes live play and means nothing. `trap_size_fraction` follows it:
it feeds only the trap ceiling, which a zeroed `w_articulation` switches off.

Selection stripped the territory and exploration terms almost to zero and kept a moderate
ramped distance-keeper. That is a coherent answer to a pool with sealers in it — and it is
also what breaks it.

## 4. The gate says no

Held-out seeds 1–32, disjoint from the GA's 401–432, both physics, seven cop arms, each
thief vector run **informed and blind** so the M7-21 caveat (the gain is conditional on the
cop declaring) is measured rather than assumed.

**Counted physics (`multiplicative_book_v1`)** — aggregate favours the candidate:
2220 v 2200 informed, 1985 v 1975 blind. Per arm, survivals of 32:

| cop arm | champion (inf/blind) | m7-30 (inf/blind) | |
|---|---|---|---|
| ref-police | 30 / 12 | **32 / 13** | better |
| greedy-loud | 30 / 6 | **32 / 6** | better / tie |
| sealer-loud | 30 / 27 | **31 / 29** | better |
| random, greedy-quiet, sealer2-quiet | 32 / 32 | 32 / 32 | tie |
| **sealer-quiet** | **30 / 30** | **29 / 29** | **WORSE, both feeds** |

**Reference physics (the no-regression half)** — the informed rows are clean (m7-30 tops
the table at 2240, 32/32 against every arm), but blind it collapses: against `greedy-loud`
it survives **0 of 32**, where the champion survives 8 and the base table survives 32.

Per CLAUDE.md §5 the rule is beat-or-tie on **every** arm. It regresses on the arm the
milestone was aimed at — a quiet waller, the closest model of the cop that actually beat
us — and it loses a whole arm blind under the physics it was not tuned for. **It does not
ship.** The weights are kept as a labelled negative-result artifact
(`config/ga_weights_bookv1_walling.json`), the M7-20 precedent.

The failure is legible: zeroing `w_region` and `w_spread` makes the thief a near-pure
distance function — sharper against cops it can see, and predictable to a chaser it cannot.

## 5. Two arms that prove nothing, recorded so nobody reads them as evidence

`greedy-quiet` (M7-21's gate carried it, and so does this one for continuity) is a **dead
column by construction**: `claim_threshold` 2.0 means it never declares, the book's scoring
table 2 makes a landing capture conditional on the declaration, and a chaser that places no
barriers has no other capture form — so it returns 32/32 to any thief whatsoever.

Checked against M7-21's own generated tables rather than asserted: its book-v1 gate had
`greedy-quiet` at 32 v 32 **and `random` at 32 v 32**, so its "124/128, better-or-equal on
every arm" was carried by exactly **two** arms — `ref-police` (30 v 21) and `greedy-loud`
(30 v 21). Its reference gate is the same shape. `sealer2-quiet` here is a third instance
for a different reason (its exit ceiling of 2 rarely triggers). That is M7-20's
`random`-discriminates-0.000 finding recurring three times, and it is why this milestone's
gate runs seven arms in two feed conditions rather than four.

The dated correction is written into `m7-21-informed-thief.md` §0 and the TODO M7-21 entry
beside their original text (M7-20/#83 precedent), not only here.

The quiet **sealers** are the arms that matter: going silent costs a walling cop nothing,
because the barrier and imprisonment forms are never claim-gated. That is the M7-19 finding
read from the opponent's side, and it is the shape of the cop that beat us.

## 6. Open decision, and the follow-up that is not ours to make here

**`w_articulation` on the book-v1 overlay — ANSWERED 2026-08-02: NO, the deployed weights
stay as they are.** The question put to Imree was whether to zero it. The instrument
certifies a tie (768 games, every cell identical between 8.93 and 0.0), so zeroing it was
**not justified by a win** — no win on that gene is measurable in this tree at all — only by
*agreement*: 0.0 is the only value at which arena and wire provably do the same thing. The
scratchpad measurements in §1 pointed the same way but are not reproducible here, so they
were support and not the argument. **His decision: no change.** The overlay keeps 8.93, and
the live-versus-measured divergence it carries is closed by fixing the instrument (M7-31)
rather than by moving a weight the gate cannot score.

**Follow-up — M7-31, police-lead (mirrored core, not editable from this repo), claimed:**
`referee_obs.thief_observation` must carry the barrier quota the peer path already passes.
Until it does, no thief retune can tune trap-awareness, and
`test_referee_mode_cannot_see_the_gene` is expected to go red the moment it lands — it
should be deleted by the same commit.

**Follow-up, strategy:** a trap detector that sees k-barrier seals, not just single cuts
(§1c). §1d rules out the two cheap shapes; this needs its own PRD, not a weight.

## 7. What is NOT claimed

- The sealers are a **model** of the tactic, not of the opponent. His cop has belief-driven
  placement we cannot replicate; our arm chases and seals opportunistically. That the
  champion holds 30/32 against our model says nothing about the cop that beat us 3–0.
- No claim that the deployed vector is good against sealing cops — only that no vector this
  run found is *better* on every arm.
- The scratchpad findings in §1(a)–(d) are disclosed as unreproducible from this tree.
- No cop weights were touched, in either repo. No live behaviour changed by this milestone.
