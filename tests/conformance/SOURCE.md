# Conformance fixtures — provenance

The JSON files under `vectors/` are copied **verbatim** from the league conformance kit
(<https://github.com/Imreec/copthief-league-protocol>), the byte authority for the book v3.0.0
constructions (kit SPEC §2–§5; CLAUDE.md §1 #13). They are never hand-edited here: the kit is the
generator — on a kit revision, re-copy and re-verify (PRD_crypto §7).

- Kit commit: `5b3927ef8a3de9002f1881127869ab411b7401ca` (main, "Merge pull request #3 —
  rescope/interop-kit-book-v3")
- Copied at M1-3: `canonical_json.json`, `commit_reveal.json` (incl. `divergent_forms`),
  `terms_signature.json`, `game_uid.json`
- Joins at M3-2 (with `domain/scent`): `pheromone.json`
- Not copied (ENH, opt-in only): `joint_seed.json`, `derive_starts.json`
