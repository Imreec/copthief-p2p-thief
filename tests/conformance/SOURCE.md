# Conformance fixtures — provenance

The JSON files under `vectors/` are copied **verbatim** from the league conformance kit
(<https://github.com/Imreec/copthief-league-protocol>), the byte authority for the book v3.0.0
constructions (kit SPEC §2–§5; CLAUDE.md §1 #13). They are never hand-edited here: the kit is the
generator — on a kit revision, re-copy and re-verify (PRD_crypto §7).

- Kit commit: `5b3927ef8a3de9002f1881127869ab411b7401ca` (main, "Merge pull request #3 —
  rescope/interop-kit-book-v3")
- Copied at M1-3: `canonical_json.json`, `commit_reveal.json` (incl. `divergent_forms`),
  `terms_signature.json`, `game_uid.json`
- Copied at M3-2 (with `domain/scent`): `pheromone.json` (LF-rewritten per repo convention)
- Copied at M3-8 from kit commit `c12e4e9` (main, "Merge pull request #8 —
  feat/promote-book-v1"): `locked_model.json` (SPEC §7 doc schema, six registrations, the
  five-row refusal truth table), `scent_book_v3.json` (SPEC §5.1 `multiplicative_book_v1`,
  **PROMOTED** — anrbj666's independent implementation reproduced every case byte-exact)
- Not copied (ENH, opt-in only): `joint_seed.json`, `derive_starts.json`

The JSON files under `sample_run/` are copied **verbatim** (LF-rewritten) from the reference
implementation's published `docs/sample-run/` at oracle sha `960499fd` (ADR-0002 log entry
2026-07-19; PRD_reporting §9 D4 — approved attributed fixtures). They byte-pin the M6-2 report
artifacts: every embedded hash (group signatures, config lock, log/result consensus signatures)
must recompute through our code, and every file must reproduce from our serializer
(`test_report_sample_run.py`). Regenerate only by re-copying from a new reference sha.

- Reference commit: `960499fd5e8777b4929625f5d8fdcf2ab4677b54` (v3.0.0)
- Copied at M6-2: `declaration_…json`, `config_…_g01.json`, `log_…_g01.json`, `result_…json`
  (game_id `segal-police-team-vs-segal-thief-team`)
