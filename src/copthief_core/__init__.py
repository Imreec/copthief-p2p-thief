"""copthief_core — role-agnostic engine, protocol, and infrastructure (MIRRORED).

This package is developed in the police (lead) repo and mirrored byte-identically into the
thief repo by ``scripts/sync_core.py``; CI verifies ``sync_manifest.json`` in both repos.
Never edit this package in the thief repo. Packages arrive per docs/PLAN.md §3 as their
milestones land (M1: domain, wire, peer, infra, sdk, shared).
"""

__all__ = ["__version__"]
__version__ = "1.00"
