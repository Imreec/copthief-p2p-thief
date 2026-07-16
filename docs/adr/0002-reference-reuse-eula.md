# ADR-0002 — Reference-implementation reuse: interface-mirror + live oracle

**Status:** Accepted (Phase 1 grill, 2026-07-16; approved by Imree).

## Context

The official reference implementation (`github.com/rmisegal/Game-P2P-Cop-Chase`, Educational-Use
EULA) may, per the book's App D, be used in parts, studied, and modified for the project — but
"do not start the project from this repo," and EULA §4c forbids redistribution to non-students.
Our repos are private-shared, so incorporation is legally viable; the question is engineering and
narrative: the rubric grades our ability to specify and generate our own system.

## Decision

**All code is ours.** We deliberately mirror the reference's *contracts*: MCP tool names
(`negotiate`, `receive_turn`, `submit_audit`, `receive_control`), the
`TurnMessage`/`AuditPayload`/`ControlMessage` field sets, the negotiate→turns→audit sequence, and
the `BrainBase`-style strategy seam. We exercise the strongest EULA-granted right — **executing**
the reference — by running its peer as our first live opponent (the M2 oracle spike and ongoing
regression). Byte-level constructions come from our public conformance kit, which pinned them
against the reference with attribution. Micro-snippet allowance: byte-critical fragments of a few
lines (the canonical `json.dumps` call form, the `state` string format) may be transplanted; each
such transplant is recorded in this ADR's log below with file + provenance.

**Repos stay private-shared with the lecturer for the project's lifetime** (also ADR'd in
CLAUDE.md §1 #17); flipping public would require re-verifying that no EULA-covered material is
included.

## Micro-snippet log

*(none yet)*

## Consequences

Zero EULA exposure in practice; authorship story clean; conformance verified by observation
(running oracle) rather than by trusting our reading; slight extra cost re-deriving utilities the
kit already pins (accepted).

## Alternatives considered

Strict clean-room (slower, no oracle leverage — rejected); transplanting whole utility modules
(blurs authorship, unnecessary given the kit — rejected); fork-and-extend (App D warns against
it; forfeits the process-story points — rejected).
