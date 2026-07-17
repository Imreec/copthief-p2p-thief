"""copthief_core.peer — the orchestrator layer: handshake, sealing, turn loop, audit.

Single gateway for everything protocol-side (PRD FR-8): drives the domain state machine,
seals every turn through domain.crypto, and treats every inbound byte as adversarial
until validated (wire layer first, then protocol checks).
"""

__all__ = ["__version__"]
__version__ = "1.00"
