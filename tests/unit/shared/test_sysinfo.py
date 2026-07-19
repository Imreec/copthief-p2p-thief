"""shared/sysinfo (M6-3): best-effort hardware + commit-hash collection.

Every probe must degrade to "unknown" and NEVER raise — a spec probe failure at
game start must not cost a technical loss. Results are process-cached (the peer
seals one step-0 record per sub-game; probing is not per-turn work).
"""

from __future__ import annotations

import json
import subprocess

import pytest

from copthief_core.shared import sysinfo

SPEC_KEYS = {
    "os",
    "cpu_type",
    "cpu_cores",
    "cpu_freq_mhz",
    "ram_gb",
    "gpu_type",
    "gpu_cores_or_cuda",
    "vram_gb",
}


@pytest.fixture(autouse=True)
def _fresh_caches() -> None:
    sysinfo.collect_spec.cache_clear()
    sysinfo.current_commit_hash.cache_clear()


def test_collect_spec_returns_exactly_the_reference_key_set() -> None:
    spec = sysinfo.collect_spec()
    assert set(spec) == SPEC_KEYS
    json.dumps(spec)  # must be JSON-serializable (it goes inside the sealed record)


def test_collect_spec_never_raises_when_every_probe_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*args: object, **kwargs: object) -> object:
        raise OSError("probe down")

    monkeypatch.setattr(sysinfo.platform, "system", boom)
    monkeypatch.setattr(sysinfo.platform, "processor", boom)
    monkeypatch.setattr(sysinfo.os, "cpu_count", boom)
    monkeypatch.setattr(sysinfo.subprocess, "run", boom)
    spec = sysinfo.collect_spec()
    assert set(spec) == SPEC_KEYS
    assert spec["os"] == "unknown"
    assert spec["gpu_type"] == "unknown"


def test_current_commit_hash_is_the_real_repo_head() -> None:
    """The M6-3 DoD: the hash the step-0 record declares IS this checkout's HEAD."""
    expected = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    observed = sysinfo.current_commit_hash()
    assert observed == expected
    assert len(observed) == 40
    assert all(c in "0123456789abcdef" for c in observed)


def test_current_commit_hash_degrades_to_unknown_without_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_git(*args: object, **kwargs: object) -> object:
        raise FileNotFoundError("git not on PATH")

    monkeypatch.setattr(sysinfo.subprocess, "run", no_git)
    assert sysinfo.current_commit_hash() == "unknown"
