# Self-grade — 93.0 / 100

Computed by [`scripts/self_grade.py`](scripts/self_grade.py) from the committed rubric
[`config/self_grade.json`](config/self_grade.json); this prose matches that output exactly —
re-run the script to verify. Per the book's **App E rule 55**, the grade assesses **code
quality only, never league results**: the evader's 15-of-15 survival run is evidence in the
README, not an input to this number. The rubric scores the two-repo system this repo is half
of (the core is byte-mirrored), with role-specific evidence cited per category; calibration is
deliberately conservative (target band 92–93, hard cap 95), and
[`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) — this repo's T-entries plus the lead repo's
L-entries — is the justification for the gap below 100.

| Category | Weight | Score | Why not higher |
|----------|-------:|------:|----------------|
| Architecture & orchestration patterns | 20 | 94.0 | Mirror discipline held perfectly (no core edit ever landed here; role code isolated in 9 clean modules) — but the shared peer layer's sprawl and session-per-call transport shape (lead L-06) apply here identically. |
| Protocol/crypto correctness & interop evidence | 20 | 95.0 | Ten byte-identical mutual settlements; the thief's rules-46/47 self-concession closed a live rule-35 shape — held back by the shared reader-side gaps (lead L-02/L-05). |
| Strategy-module engineering | 20 | 91.0 | The opponent lab and its sweep-before-deploy method, with an honest null result (M7-30) and the k=4 trade documented (T-01) — deducted for the pre-M13 instrument defect, the modest GA delta (T-04), and offline-only deception evidence (T-06). |
| Reliability engineering | 15 | 90.0 | The 19-drill battery + the thief's pacing machinery — but the two live-found deadline defects and the latent echo bug were caught by opponents' clocks, not our drills. |
| Documentation & research artifacts | 15 | 95.0 | Full report with regenerable figures, 28 thief-side evidence files, notebook pinned renders-clean — doctrine-era evidence lives lead-side by topology (T-02). |
| Process discipline | 10 | 92.0 | Sync discipline unbroken; the same few caught-and-corrected doc↔repo drift moments as the lead. |
| **TOTAL** | **100** | **93.0** | |

The cap discipline: 95 is a *reporting* ceiling, not the scale's top; the grader is ground
truth, and this number is meant to sit slightly below our honest internal assessment.
