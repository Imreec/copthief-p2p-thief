"""Anti-pattern scanner (CLAUDE.md §10) — mechanical subset of the banned list.

Checks: no NotImplementedError placeholders in src/ · no leaked machine-local paths ·
no "AI Agent" author strings · Python-version pins stay in sync across pyproject sections.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

LEAK_PATTERNS = [r"C:\\Users\\", r"/mnt/[a-z]/", r"/home/\w+/"]
SCAN_SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".json"}
SELF = Path(__file__).name


def iter_files() -> list[Path]:
    """Tracked-ish scan set: src, tests, scripts, docs, config, root files."""
    roots = [Path("src"), Path("tests"), Path("scripts"), Path("docs"), Path("config")]
    files = [p for r in roots if r.is_dir() for p in r.rglob("*") if p.suffix in SCAN_SUFFIXES]
    files += [p for p in Path().glob("*") if p.suffix in SCAN_SUFFIXES]
    return files


def check_content(problems: list[str]) -> None:
    """Scan file contents for banned patterns."""
    for path in iter_files():
        if path.name == SELF:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path)
        if path.parts and path.parts[0] == "src" and "NotImplementedError" in text:
            problems.append(f"{rel}: NotImplementedError placeholder in src/")
        for pat in LEAK_PATTERNS:
            if re.search(pat, text):
                problems.append(f"{rel}: leaked machine-local path ({pat})")
        # CLAUDE.md documents this ban verbatim — the rule targets author strings elsewhere.
        if path.name != "CLAUDE.md" and ('"AI Agent"' in text or "'AI Agent'" in text):
            problems.append(f'{rel}: "AI Agent" author string')


def check_version_sync(problems: list[str]) -> None:
    """requires-python, ruff target-version, and mypy python_version must agree."""
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    requires = data["project"]["requires-python"]  # e.g. ">=3.12"
    m = re.search(r"(\d+)\.(\d+)", requires)
    if m is None:
        problems.append("pyproject: cannot parse requires-python")
        return
    expect = f"py{m.group(1)}{m.group(2)}"
    ruff_target = data["tool"]["ruff"]["target-version"]
    mypy_ver = data["tool"]["mypy"]["python_version"]
    if ruff_target != expect:
        problems.append(f"pyproject: ruff target-version {ruff_target} != {expect}")
    if mypy_ver != f"{m.group(1)}.{m.group(2)}":
        problems.append(f"pyproject: mypy python_version {mypy_ver} != {m.group(1)}.{m.group(2)}")


def main() -> int:
    """Run all checks; report and exit non-zero on any hit."""
    problems: list[str] = []
    check_content(problems)
    check_version_sync(problems)
    if problems:
        print("FAIL: anti-patterns found:")
        for p in problems:
            print(f"  {p}")
        return 1
    print("OK: no banned anti-patterns detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
