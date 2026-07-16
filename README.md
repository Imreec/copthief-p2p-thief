# copthief-p2p-thief — Thief agent, Distributed Cops-and-Robbers over P2P

> **Status: M0 (process bedrock) — no gameplay code yet, by design.** This project builds
> docs-first behind approved gates: see [docs/PRD.md](docs/PRD.md), [docs/PLAN.md](docs/PLAN.md),
> [docs/TODO.md](docs/TODO.md). This README becomes the full academic report at M8; until then it
> only states what is true of the tree.

Final project, *Orchestration of AI Agents* (University of Haifa, Dr. Yoram Segal) — the **thief**
agent for the hidden-position pursuit race over P2P FastMCP, per the official book v3.0.0 and its
binding parameters table. **Sibling repo (cop agent, lead):**
[copthief-p2p-cop](https://github.com/Imreec/copthief-p2p-cop). Byte-level interop follows our
public conformance kit:
[copthief-league-protocol](https://github.com/Imreec/copthief-league-protocol).

## What exists right now

- Approved planning docs (PRD / PLAN / TODO) + `CLAUDE.md` (project law) + ADRs 0001–0002.
- Quality gates wired: ruff, mypy --strict, pytest+coverage, 150-line limit, anti-pattern /
  no-hardcoded scanners, core-mirror manifest check, self-grade validation, submission checklist.
- **Mirror discipline (ADR-0001):** `src/copthief_core/`, skills, workflows, `scripts/`, and
  `docs/REVIEW_PROCESS.md` are developed in the sibling (lead) repo and arrive here as
  `sync: core from police@<sha>` commits, verified by `sync_manifest.json` in CI. Role-specific
  work (the ThiefBrain, `config/`, docs, this README) happens here.

## Development

```bash
uv sync          # install (dev tooling only at M0; keyless)
make grade       # every quality gate, same as CI
```

Process: branch → PR → cross-model review → squash-merge (`docs/REVIEW_PROCESS.md`). No email is
ever sent by tooling without an explicit human arming step.
