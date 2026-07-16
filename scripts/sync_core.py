"""Core-mirror sync (ADR-0001, PLAN §11): police repo is lead; thief receives byte-identical
copies of the MIRRORED paths. ``sync_manifest.json`` pins per-file SHA-256 + a tree hash; CI in
BOTH repos runs ``--verify`` so any drift fails the build.

Usage:
  uv run python scripts/sync_core.py --write-manifest   # lead: refresh manifest from local files
  uv run python scripts/sync_core.py --verify           # both: manifest must match local files
  uv run python scripts/sync_core.py --sync             # lead only: copy to sibling + manifest
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

MIRRORED = [
    "src/copthief_core",
    # Core tests travel WITH the code they cover (PRD_crypto §7): without them the
    # follower's coverage gate cannot hold. Role-package tests (tests/unit/test_packages.py)
    # stay per-repo — they import the role package and legitimately differ.
    "tests/unit/domain",
    "tests/unit/shared",
    "tests/integration",
    "tests/conformance",
    ".claude/skills",
    ".github/workflows",
    "docs/REVIEW_PROCESS.md",
    "scripts",
]
MANIFEST = Path("sync_manifest.json")
LEAD_DIR, FOLLOWER_DIR = "copthief-p2p-cop", "copthief-p2p-thief"


def repo_root() -> Path:
    """Root of the current repo (cwd must be inside it)."""
    return Path.cwd()


def is_lead() -> bool:
    """The police repo (lead) is identified by its directory name."""
    return repo_root().name == LEAD_DIR


def _is_junk(path: Path) -> bool:
    """Untracked build/cache artifacts must never enter the manifest (CI checkouts lack them)."""
    return "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}


def mirrored_files(base: Path) -> list[Path]:
    """All files under the MIRRORED paths, junk excluded, sorted for determinism."""
    files: list[Path] = []
    for entry in MIRRORED:
        p = base / entry
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(q for q in sorted(p.rglob("*")) if q.is_file() and not _is_junk(q))
    return sorted(files)


def build_manifest(base: Path) -> dict[str, object]:
    """Per-file SHA-256 + tree hash + source commit of the lead repo."""
    hashes = {
        f.relative_to(base).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in mirrored_files(base)
    }
    tree = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    commit = (
        subprocess.run(
            ["git", "-C", str(base), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        or "unknown"
    )
    return {"source_repo": LEAD_DIR, "source_commit": commit, "tree_hash": tree, "files": hashes}


def write_manifest(base: Path) -> None:
    """Refresh the committed manifest from local mirrored files (lead only)."""
    manifest = build_manifest(base)
    (base / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"manifest written: {len(manifest['files'])} files, tree {manifest['tree_hash'][:12]}")  # type: ignore[index]


def verify(base: Path) -> int:
    """Committed manifest must match the local mirrored files exactly."""
    if not (base / MANIFEST).exists():
        print("FAIL: sync_manifest.json missing")
        return 1
    committed = json.loads((base / MANIFEST).read_text())
    current = build_manifest(base)
    if committed["files"] == current["files"]:
        print(f"OK: core mirror intact ({len(current['files'])} files).")
        return 0
    old, new = committed["files"], current["files"]
    for path in sorted(set(old) | set(new)):
        if old.get(path) != new.get(path):
            state = "missing" if path not in new else ("extra" if path not in old else "drifted")
            print(f"  {state}: {path}")
    print("FAIL: core mirror drift — run sync_core.py --sync from the lead repo.")
    return 1


def sync(base: Path) -> int:
    """Lead only: copy mirrored paths to the sibling and write its manifest."""
    if not is_lead():
        print(f"FAIL: --sync runs only from the lead repo ({LEAD_DIR}).")
        return 1
    sibling = base.parent / FOLLOWER_DIR
    if not sibling.is_dir():
        print(f"FAIL: sibling not found at {sibling}")
        return 1
    dirty = subprocess.run(
        ["git", "-C", str(sibling), "status", "--porcelain", "--", *MIRRORED, str(MANIFEST)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if dirty:
        print("FAIL: sibling has uncommitted changes in mirrored paths — commit or revert first:")
        print(dirty)
        return 1
    for entry in MIRRORED:
        src, dst = base / entry, sibling / entry
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        elif src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
    write_manifest(base)
    shutil.copy2(base / MANIFEST, sibling / MANIFEST)
    commit = json.loads((base / MANIFEST).read_text())["source_commit"]
    print(f"synced -> {sibling.name}; commit there with: sync: core from police@{commit}")
    return 0


def main() -> int:
    """Dispatch on the single required mode flag."""
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    base = repo_root()
    if mode == "--write-manifest":
        write_manifest(base)
        return 0
    if mode == "--verify":
        return verify(base)
    if mode == "--sync":
        return sync(base)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
