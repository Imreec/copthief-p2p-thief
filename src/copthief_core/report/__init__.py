"""report — artifact schemas, canonical emitters, and the settlement signature (M6-2).

PLAN §3 layer rules: depends on `domain` only; consumed through the sdk. The email
gatekeeper path (M6-4/M6-5) plugs in downstream of `emit_series`'s returned result.
"""

from copthief_core.report.builders import (
    build_config_artifact,
    build_declaration,
    build_log,
    build_result,
)
from copthief_core.report.consensus import consensus_signature
from copthief_core.report.emit import emit_series, write_artifact
from copthief_core.report.hebrew import build_report
from copthief_core.report.schemas import ReportValidationError, validate_artifact

__all__ = [
    "ReportValidationError",
    "__version__",
    "build_config_artifact",
    "build_declaration",
    "build_log",
    "build_report",
    "build_result",
    "consensus_signature",
    "emit_series",
    "validate_artifact",
    "write_artifact",
]
__version__ = "1.00"
