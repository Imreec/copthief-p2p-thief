# PRD — Crypto layer (mechanism PRD, milestone M1)

> **Status: APPROVED (gate M1-1, 2026-07-16).** **This copy: the thief repo** — the crypto
> mechanism is role-agnostic core, authored and reviewed in the police (lead) repo (ADR-0001
> docs convention); content identical apart from this note. Parent docs: `docs/PRD.md` FR-3,
> `docs/PLAN.md` §4/§6/§12. Sources of truth: book v3.0.0 ch.5 (commit-reveal) > the **conformance
> kit** (`github.com/Imreec/copthief-league-protocol`) as the byte authority — its CORE vectors
> were confirmed byte-for-byte against the official reference implementation. Covers TODO
> **M1-3**; feeds M1-6 (sealing in the peer loop) and constraint **#13** (kit CORE conformance,
> CI-blocking).

## 1. Scope & non-goals

**In scope (M1):** `copthief_core/domain/crypto` — canonical JSON, per-step commit/verify, terms
signature, `game_uid`, nonce policy, sealed-record model; `tests/conformance/` — kit CORE vectors
as permanent CI-blocking fixtures.
**Non-goals:** pheromone math (kit CORE too, but engine-side — lands with `domain/scent` at M3-2)
· ENH constructions (joint seed, derived starts — opt-in extras, built only if a pair ever signs
them) · the wire messages that *carry* commits (M1-5) · Gmail/report canonicalization (M6, same
canonical form reused).

## 2. Canonical JSON (kit §2 — the one form under every hash)

```python
json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
```

Three load-bearing details, each pinned by `canonical_json.json` vectors:
1. **`ensure_ascii=False`** — non-ASCII (Hebrew hints, emoji) stays native UTF-8, never
   `\uXXXX`-escaped. The opponent re-hashes our revealed `hint` text at audit; escaping fails
   every non-ASCII step and voids the match for both sides.
2. **Floats are permitted, shortest round-trip repr** (`0.1`, never `0.10000000000000001`) —
   protocol payloads carry floats (`decay_per_step`, hardware `ram_gb`).
3. **Sorted keys, compact separators** — construction order in code is irrelevant.

One function, one home: `domain/crypto.canonical_bytes()` (+ `canonical_hash()`); every other
module (terms, sealing, audit, M6 reports) consumes it — never a second `json.dumps` call site
with hashing intent (constraint #11).

## 3. Per-step commit / verify (kit §3; book ch.5)

```
commit = SHA256( canonical_json(payload) + "|" + nonce )        # nonce pipe-appended, NOT inside
```

`verify(payload, nonce, commit)` recomputes with **our** serializer and compares via
`secrets.compare_digest`. At audit each side re-hashes every *opponent* revealed record; any
mismatch is proof of tampering ⇒ technical loss (0/0).

**The book's contradiction, inherited resolved:** the release prints three commit constructions
(ch.5 listing: nonce inside the JSON; audit-chapter snippet: `nonce|move`; reference:
`SHA256(canonical|nonce)`). The kit pins the **reference form** — the only one of the three that
binds `state` and `intent` (the audit-snippet form leaves position/bluff rewritable) and what the
lecturer's tooling runs. We adopt the kit's choice as-is; the `divergent_forms` fixture stays in
our suite so a future mismatch is diagnosable to a specific wrong form. (Documented for the README
contradiction narrative; the kit SPEC §3 carries the full analysis.)

## 4. Sealed record & nonce policy (book ch.5 §5.3; App E)

- **Nonce:** `secrets.token_hex(16)` (32 hex chars, matching all kit vectors) — never `random`;
  one fresh nonce per sealed record; **withheld until the end-of-game audit** (per-step reveal
  sends move+hint only; `Hcommit` travels at commit time).
- **Sealed record (self-only schema, kit §3):** the payload key set is NOT a cross-team interop
  surface — each peer reveals its own records and the opponent only re-hashes them. It IS a
  self-consistency surface: seal↔store↔reveal must be byte-identical. M1 record fields: `step`,
  `state`, `position`, `move`, `intent`, `hint` (mirroring the kit's move-record vectors);
  `sub_game`, `role`, verdict/timing/tokens join when their features land (M3+). Records are
  stored verbatim at seal time (bytes, nonce, commit) — the audit and the JSONL log (M1-8) replay
  from storage, never from re-serialization.
- **`state` string:** the reference's exact format, pinned by the kit vectors:
  `f"grid={n}x{n};self={[row, col]};barriers={sorted_barriers}"` — Python list repr **with the
  space after the comma**. Self-position only (hidden-position model). This is a byte-critical
  micro-snippet: transplanting the format string gets logged in ADR-0002's micro-snippet log.
- **Four-phase sequence (ch.5):** Commit → Acknowledge (opponent locks) → Reveal (move + hint,
  nonce still hidden) → Final Reveal at audit (all nonces). The state machine (PRD_engine §3)
  encodes this; the crypto module supplies seal/verify only.

## 5. Terms signature (kit §4)

`signature = SHA256(canonical(terms) + "|" + nonce)` — same construction as a commit, over the
agreed terms. Each peer signs with its **own** nonce; we verify the opponent's signature over the
terms *we* hold (which must value-equal theirs) using *their* nonce. Any mismatch (a value, a key
name, float repr, escaping) ⇒ refuse to play, loudly.

**Terms extraction** (`terms_from_config` equivalent): the terms dict is a *mapped* extraction
from `game.json` — the kit vectors use the **reference's key names**, which differ from the
`game.json` schema names. Pinned mapping (M1, from the kit's `terms_signature.json` key set):

| terms key | source `game.json` key |
|---|---|
| `board_size` | `board_and_agents.grid_size` |
| `smell_grid_size` | `pheromones.pheromone_grid_size` |
| `decay_per_step` | `pheromones.pheromone_decay` |
| `emit_intensity` | `pheromones.pheromone_center_intensity` |
| `min_center_intensity` | *reference-only param; kit-pinned default 0.5 (not in App B/App F — see §8.2)* |
| `max_steps` | `movement_and_barriers.max_moves` |
| `barriers_max` | `movement_and_barriers.max_barriers` |
| `setting` | `world.map_area` |
| `hint_max_words` | `world.hint_max_words` |
| `axis_origin_corner` / `axis_start_index` | `board_and_agents.*` (same names) |
| `thief_start` / `cop_start` | `board_and_agents.*` (same names) |
| `num_games` | `network_and_league.num_games` |

## 6. `game_uid` (kit §4)

```
game_uid = str(UUID( SHA256( canonical(terms) + "|" + "|".join(sorted([group_a, group_b])) ).digest()[:16] ))
```

A pure function of shared inputs — both peers derive it with no round-trip; group ids are sorted,
so order never matters (pinned by the swapped-groups vector). It names all four submission
artifacts (`declaration_/config_/log_/result_<game_id>` per App F table 20), so files from
different matches can never mix.

## 7. Conformance fixtures & CI (constraint #13)

- `tests/conformance/vectors/` — `canonical_json.json`, `commit_reveal.json` (incl.
  `divergent_forms`), `terms_signature.json`, `game_uid.json`, copied **verbatim** from the kit;
  a `SOURCE.md` records the kit commit hash. Fixtures are never hand-edited here — the kit is the
  generator; a kit revision re-imports + re-verifies (`pheromone.json` joins at M3-2 with
  `domain/scent`).
- One test module per vector file, driving **our** `domain/crypto` (not a vendored checker) over
  every vector. CI-blocking in both repos. `tests/` is not currently a mirrored path, so M1-3
  extends `sync_core.py`'s `MIRRORED` with the core test tree (`tests/core/` +
  `tests/conformance/`; role-package tests stay per-repo) — conformance and core tests ride the
  same manifest-gated channel as the code they exercise.
- **Process rule (constraint #13):** any change touching wire format, canonicalization, or hashing
  re-runs the conformance suite and is re-verified against the kit before merge.

## 8. Documented items & open questions

1. **Commit-form contradiction** — resolved by kit adoption (§3); named in the README
   contradiction narrative at M8.
2. **`min_center_intensity`** — appears in the kit's pinned terms (default 0.5) but in neither
   App B's listing nor App F's table; it is the reference's emission gate (kit §5). Carried in
   our terms for byte-compatibility; its App F status is treated as *negotiable with default
   0.5*. Flagged for the M2 spike notes.
3. **Terms extraction key set vs the running reference** — the kit pins constructions given a
   terms dict; the exact extraction is the reference's `terms_from_config`. §5's mapping is our
   M1 pin; **M2 verifies it byte-for-byte against the live reference peer** (added to the M2-2
   verification list; a mismatch there fails the negotiate gate visibly, which is exactly what
   the spike exists to catch).

## 9. Test plan (TDD; DoD of M1-3)

Conformance: every CORE vector in §7 reproduced by our code (the M1 exit criterion "kit CORE
vectors green in both repos' CI"). Unit (happy + error): canonical — key-order invariance, Hebrew
+ astral emoji, float reprs, literals/arrays · commit — reproducibility, single-bit payload
change breaks verify, wrong nonce breaks verify, all three divergent forms distinct and matched ·
terms — signature verify with opponent nonce, refusal on any value/key/float drift, extraction
mapping from a full App B `game.json` · game_uid — group-order invariance, terms sensitivity,
artifact-name derivation · nonce — length/charset, uniqueness across records, `secrets`-sourced
(no `random` import in module, asserted by test). Coverage ≥ 90% (target: full branch on this
module), files ≤ 150 lines, `mypy --strict`, ruff clean.

## 10. Acceptance criteria (binary)

- `tests/conformance/` green in keyless CI **in both repos** (post-sync), fixtures byte-identical
  to the kit at the recorded commit.
- A seal→store→reveal→verify round-trip over a record containing a Hebrew hint passes; the same
  record with any mutated field fails verify — both observed in tests.
- `domain/crypto` is pure (no I/O/clock/network) and is the repo's only hashing/serialization
  call site with protocol intent.
