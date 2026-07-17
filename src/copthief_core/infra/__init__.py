"""copthief_core.infra — swappable adapters only (PLAN §3): transport, later LLM/Gmail.

CI is keyless: the in-process MCP fake stands in for FastMCP here; the real
network-facing adapters arrive with the M1-7 CLI and are exercised by opt-in
`@pytest.mark.live` runs, never by CI.
"""

__all__ = ["__version__"]
__version__ = "1.00"
