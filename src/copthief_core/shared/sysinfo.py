"""Best-effort host spec + commit-hash collection (M6-3; PRD_reporting §4).

Feeds the sealed step-0 declaration and the handshake identity (F8b). Stdlib only;
every probe degrades to "unknown" and NEVER raises — a spec-probe failure at game
start must not cost a technical loss. Process-cached: one probe pass serves every
sub-game (`cache_clear()` exists for tests).
"""

from __future__ import annotations

import ctypes
import os
import platform
import subprocess
import sys
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

# Operational probe budget (not a game value): a hung external probe (nvidia-smi,
# git) must never stall game start longer than this.
_PROBE_TIMEOUT_SECONDS = 5


def _probe(fn: Callable[[], object]) -> object:
    """Run one probe; any failure or empty answer becomes the string "unknown"."""
    try:
        value = fn()
    except Exception:  # noqa: BLE001 - degrade-to-unknown is this module's contract
        return "unknown"
    return "unknown" if value in (None, "") else value


def _os_name() -> str:
    return f"{platform.system()} ({platform.version()})"


def _cpu_freq_mhz() -> int | None:
    # sys.platform (not platform.system()) so mypy checks each branch only on its
    # own platform — winreg/windll have no stubs elsewhere.
    if sys.platform == "win32":
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        )
        with key:
            return int(winreg.QueryValueEx(key, "~MHz")[0])
    with open("/proc/cpuinfo", encoding="utf-8") as lines:
        for line in lines:
            if line.lower().startswith("cpu mhz"):
                return int(float(line.split(":")[1]))
    return None


def _ram_gb() -> float | None:
    if sys.platform == "win32":

        class _MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = _MemoryStatus()
        status.dwLength = ctypes.sizeof(_MemoryStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return round(float(status.ullTotalPhys) / 1024**3, 1)
    # POSIX branch: os.sysconf exists only there, so it is reached through an
    # Any-typed alias — Windows type stubs (mypy local, IDE) omit the attribute.
    posix_os: Any = os
    return round(
        int(posix_os.sysconf("SC_PAGE_SIZE")) * int(posix_os.sysconf("SC_PHYS_PAGES")) / 1024**3,
        1,
    )


def _gpu_row() -> list[str]:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        timeout=_PROBE_TIMEOUT_SECONDS,
        check=True,
    )
    return [part.strip() for part in out.stdout.splitlines()[0].split(",")]


@cache
def collect_spec() -> dict[str, Any]:
    """The eight-key host spec the reference's declaration schema expects.

    Output: JSON-serializable dict; unprobeable fields carry "unknown".
    """
    gpu = _probe(_gpu_row)
    gpu_row = gpu if isinstance(gpu, list) and len(gpu) == 2 else None
    return {
        "os": _probe(_os_name),
        "cpu_type": _probe(platform.processor),
        "cpu_cores": _probe(os.cpu_count),
        "cpu_freq_mhz": _probe(_cpu_freq_mhz),
        "ram_gb": _probe(_ram_gb),
        "gpu_type": gpu_row[0] if gpu_row else "unknown",
        "gpu_cores_or_cuda": "cuda" if gpu_row else "unknown",
        "vram_gb": round(int(gpu_row[1]) / 1024, 1) if gpu_row else "unknown",
    }


@cache
def current_commit_hash() -> str:
    """The exact commit hash of this checkout (the step-0 declaration's provenance
    claim, rules 37–38); "unknown" outside a git checkout or without git."""

    def head() -> str:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=True,
        )
        value = out.stdout.strip()
        return value if len(value) == 40 else ""

    result = _probe(head)
    return result if isinstance(result, str) else "unknown"


@cache
def commit_for_module(module: str) -> str:
    """HEAD of the git checkout that owns `module` (M7-33 role-aware provenance).

    A two-repo team's thief games run brain code from the thief repo (junction on
    PYTHONPATH), so "the exact commit played" is that repo's HEAD, not the runner's.
    Resolves the module's file and asks git from its directory; "unknown" when the
    module, its file, or a surrounding checkout cannot be resolved.
    """

    def head() -> str:
        import importlib

        source = getattr(importlib.import_module(module), "__file__", None)
        if source is None:
            return ""
        out = subprocess.run(
            ["git", "-C", str(Path(source).parent), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=True,
        )
        value = out.stdout.strip()
        return value if len(value) == 40 else ""

    result = _probe(head)
    return result if isinstance(result, str) else "unknown"
