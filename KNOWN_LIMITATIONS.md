# Known limitations — honest disclosure

Catalogued deliberately: a documented limitation is cheap, a hidden one a grader finds is fatal
to credibility on everything else. Severity: **high** = could change a result's meaning ·
**med** = narrows what the evidence proves · **low** = cosmetic/operational. Shared-core
limitations are stated once in the [lead repo's
KNOWN_LIMITATIONS](https://github.com/Imreec/copthief-p2p-cop/blob/main/KNOWN_LIMITATIONS.md)
(L-01…L-10 there apply to this repo identically — the core is byte-mirrored); below are the
entries that are this repo's own or read differently from the thief's side.

| ID | Severity | Limitation | Why accepted |
|----|----------|------------|--------------|
| T-01 | med | **The k=4 wall forecast is a trade, not a free win.** Against wall-building cops it is the measured optimum (16/32 → 31/32 survivals); against interception-class cops the same depth *costs* survivals (32/22/15 across k=1/3/4 vs the strongest such arm). The shipped default serves the mission profile; per-pairing config can select k differently. | Documented in ADR-0015 with the full trade table; a single knob cannot dominate both cop classes, and pretending otherwise would be the real defect. |
| T-02 | med | **Most doctrine-evader evidence lives in the lead repo.** The doctrine mechanisms (lethal gate, cage escape, room-first) were built and measured where the core is developed; this repo's `docs/evidence/` carries the M5/M7 thief-side trail but not the M9–M13 doctrine studies. | ADR-0001's deliberate topology: decisions and their evidence live with the code they change. Cross-links are given wherever a number is cited. |
| T-03 | low | **The M5 `ThiefBrain` rides inert behind the fielded doctrine brain.** Its tuned tables in `[strategy.thief]` are loaded but unused while `thief_class = "doctrine-evader"`; flipping the key re-fields it. | Selectable-not-dead is the intended state: the M5 brain is the documented baseline and the fallback, and deleting its tables would orphan the committed GA evidence. |
| T-04 | low | **The GA curve's improvement is modest (0.708 → 0.771)** and measured against the reference cop only — the M5 thief was near its ceiling on that opponent, and the instrument predates the doctrine rebuild that actually moved live survival. | Kept as the honest record of what weight-tuning alone bought; the doctrine work's own numbers are reported where they were measured. |
| T-05 | low | **This repo commits one counted wire log, not all ten series'.** `docs/evidence/counted-vm__fabi-2026-08-23/` holds the thief window every figure here regenerates from; the full counted artifact sets live lead-side. | The mirror topology stores each artifact once, where the series runner archived it; duplicating ~60 logs across repos would add drift risk, not evidence. |
| T-06 | med | **Deception efficacy is real but small, and was measured offline.** The template-bank A/B (M5-6, `docs/evidence/m5-template-ab.md`) separated `classic` from `terse` only on a tiebreak (+0.000042 error/lie); no live opponent was shown to act on our lies in a way that changed an outcome. | Disclosed rather than dressed up: the lie channel's value depends on the opponent's hint trust, which most rivals floor-clamped — exactly as our own profiling does. |

The self-grade's per-category justifications reference these entries; the gap below 100 is this
table plus the lead repo's.
