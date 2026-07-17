"""copthief_core.wire — the interface-mirrored message contract (PLAN §6; ADR-0002).

Field sets mirror the reference implementation's `TurnMessage` / `AuditPayload` /
`ControlMessage`. Validation rule (PRD FR-2): every inbound message is validated before
any state changes — missing required fields reject, unknown fields are tolerated and
preserved (forward compatibility). Depends on nothing (PLAN §3).
"""

__all__ = ["__version__"]
__version__ = "1.00"
