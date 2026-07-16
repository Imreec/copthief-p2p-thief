# Review Process

> How work reaches `main`: terminal authoring → automated quality gates → independent cross-model
> review → human adjudication.

## Pipeline

1. **Authoring (terminal).** Code is written via the Claude Code CLI under Imree's direction
   (`CLAUDE.md §8`). An IDE may serve as editor/shell; no IDE-coupled inline AI completion.
2. **Automated gates (CI + pre-commit).** Every commit and PR runs `ruff` (+format), `mypy
   --strict`, `pytest` with coverage `fail_under`, the ≤150-line file-size check, the
   anti-pattern / no-hardcoded scanners, the core-mirror manifest check, and (from M1) the kit
   CORE conformance vectors. Nothing merges red (`CLAUDE.md §1`).
3. **Independent cross-model review.** Each pull request is reviewed by a **separate model
   family** (different from the authoring model), which posts findings **as PR comments** — a
   verifiable trace on the PR itself.
4. **Human adjudication.** Imree (driver) and Eyal (reviewer) read the review, accept or push
   back on each finding with reasoning, and address accepted ones with follow-up commits on the
   same branch. Each resolution is replied to on the thread.

## Why a different model reviews

Author and reviewer are **different models**, so the reviewer is not anchored to the author's
assumptions and brings different blind spots — the same rationale that makes independent peer
review standard. It does not replace human judgment; the humans make the final call.

## Findings are verified, not obeyed

Every review finding is checked against the primary sources before acceptance — the book v3.0.0
+ its binding parameters table, the conformance kit, the course guidelines, then our approved
docs. **A citation is opened and read before it is trusted**; a [Blocking] verdict requires a
verified conflict with a primary source, quoted and located. Rejections are documented with
reasoning, same as acceptances.

## On the record (this project)

The Phase-2 planning gates ran through this pipeline on local files (pre-repo); the trace moves
to PR comments now that the repos exist:

- **PRD review:** 2 of 3 findings accepted and fixed (config-owned value naming → binding
  `game.json` keys everywhere; an App F validation guard added to FR-4). 1 finding **rejected
  with sources**: a separate `rate_limits.json` is book-sanctioned (App B), reference-shipped,
  and guidelines-mandated — the useful kernel (precedence vs the signed `game.json` block) was
  adopted. The review also cited a non-existent `REVIEW_DIGEST.md`; feedback was issued and the
  verify-citations rule above was made standing law.
- **PLAN review:** verdict clean; one naming nit resolved **toward the book** — the
  `_g<NN>` per-mini-game artifact suffix is mandated by App F's files table and confirmed by the
  reference's `docs/sample-run/`; the kit's SPEC §4 shorthand gets clarified instead (M7-2).
