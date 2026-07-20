"""M7-7(2)+(3): the watchdog's operational artifacts stay out of the tree, and loudly.

(2) `peer_run` derived the snapshot directory from `log_path.parent`, so the kill drill
    — logging into `docs/evidence/` — dropped a committable `state_police.json` into a
    TRACKED directory. The snapshot is specified as a git-ignored operational artifact
    (PRD_gatekeeper §7 D4); it is now pinned to `logs/`, whatever the log path is.
(3) `os._exit(1)` skips stdout flushing, so the loud exit printed NOTHING to the
    console — the stall lived only in the JSONL. It must be written AND flushed.
"""

from __future__ import annotations

import io
from pathlib import Path

from copthief_core.peer.watchdog import announce_stall
from copthief_core.sdk.peer_run import snapshot_path

GITIGNORE = Path(".gitignore")
PEER_RUN_SOURCE = Path("src/copthief_core/sdk/peer_run.py")


def test_the_snapshot_is_pinned_to_the_gitignored_logs_dir() -> None:
    assert snapshot_path("police") == Path("logs") / "state_police.json"
    assert snapshot_path("thief") == Path("logs") / "state_thief.json"


def test_the_snapshot_path_never_follows_the_log_path() -> None:
    """The regression itself: logging into a tracked directory must write no artifact
    there. The path is role-derived, so no log path can steer it. Comment lines are
    stripped — the fix is DESCRIBED in a comment naming the old expression."""
    code = [
        line
        for line in PEER_RUN_SOURCE.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("#")
    ]
    assert "log_path.parent" not in "\n".join(code)


def test_a_stray_snapshot_anywhere_is_still_git_ignored() -> None:
    """Belt and braces: `logs/` was already ignored, but only `logs/`. A snapshot that
    escapes again — by any path — must not be committable."""
    assert "state_*.json" in GITIGNORE.read_text(encoding="utf-8")


class FlushCounting(io.StringIO):
    """A stream that remembers whether anyone flushed it before the process died."""

    def __init__(self) -> None:
        super().__init__()
        self.flushes = 0

    def flush(self) -> None:
        self.flushes += 1
        super().flush()


def test_the_stall_reaches_the_console_and_is_flushed() -> None:
    stream = FlushCounting()
    events: list[dict[str, object]] = []
    announce_stall(
        "loop stall: no heartbeat for 60.34s", role="police", sink=events.append, stream=stream
    )
    printed = stream.getvalue()
    assert "loop stall" in printed
    assert "60.34s" in printed
    assert stream.flushes >= 1  # os._exit skips this — it must happen here
    assert events == [
        {
            "event": "watchdog_stall",
            "sender": "police",
            "payload": {"reason": "loop stall: no heartbeat for 60.34s"},
        }
    ]


def test_the_stall_still_logs_when_there_is_no_jsonl_sink() -> None:
    """A live peer may run without `--log`; the console must still say what happened."""
    stream = FlushCounting()
    announce_stall(
        "transport stall: blocked in I/O for 241.0s", role="thief", sink=None, stream=stream
    )
    assert "transport stall" in stream.getvalue()
    assert stream.flushes >= 1
