"""M7-7(1): the heartbeat measures LOOP LIVENESS, not I/O duration.

The real-tunnel kill drill proved the M6-7 watchdog fired on a *healthy* loop: a
blocking outbound call held the loop inside the transport, no beat landed, and the
signed `watchdog_timeout_sec` (60) self-terminated us before the private
`turn_timeout_seconds` (180) could classify the opponent as silent. A deliberate,
bounded wait on the wire is not a wedge. Inside an I/O window the watchdog applies the
reconciled I/O budget — which sits BEHIND our own turn deadline — so a network flap is
lost by rule, never by suicide. Outside a window nothing changes, and an I/O wait that
outlasts even the I/O budget still fires: the watchdog stays a backstop, never a mute.
"""

from __future__ import annotations

from pathlib import Path

from copthief_core.peer.watchdog import Watchdog


def make_watchdog(tmp_path: Path) -> tuple[Watchdog, list[str]]:
    """A watchdog with a 10 s loop budget behind a 40 s I/O budget (scaled shape of
    the shipped 60 s / 240 s reconciliation)."""
    stalls: list[str] = []
    dog = Watchdog(
        timeout_sec=10.0,
        io_timeout_sec=40.0,
        snapshot=lambda: {"role": "police"},
        persist_path=tmp_path / "state_police.json",
        on_stall=stalls.append,
    )
    return dog, stalls


def test_a_blocking_outbound_call_past_the_loop_budget_does_not_fire(tmp_path: Path) -> None:
    """The drill's exact shape: a 30 s outbound stall on a live loop. Under M6-7 this
    self-terminated at 10 s; the loop is inside a declared I/O window, so it must not."""
    dog, stalls = make_watchdog(tmp_path)
    dog.beat(now=0.0)
    dog.enter_io(now=1.0)
    assert dog.check(now=31.0) is False  # 30 s blocked — well past the 10 s loop budget
    assert stalls == []
    assert not (tmp_path / "state_police.json").exists()


def test_a_dead_loop_outside_any_io_window_still_fires(tmp_path: Path) -> None:
    """The FR-8 guarantee is untouched: a genuinely wedged loop is never silent."""
    dog, stalls = make_watchdog(tmp_path)
    dog.beat(now=0.0)
    assert dog.check(now=10.5) is True
    assert dog.fired is True
    assert len(stalls) == 1
    assert "loop stall" in stalls[0]


def test_io_that_outlasts_even_the_io_budget_still_fires_and_names_the_transport(
    tmp_path: Path,
) -> None:
    """A transport that never returns is a wedge too — the backstop must survive, and
    its reason must not read as a loop bug when the loop was fine."""
    dog, stalls = make_watchdog(tmp_path)
    dog.beat(now=0.0)
    dog.enter_io(now=1.0)
    assert dog.check(now=41.5) is True
    assert len(stalls) == 1
    assert "transport stall" in stalls[0]
    assert (tmp_path / "state_police.json").exists()  # state persisted either way


def test_leaving_the_window_restores_the_loop_budget_and_beats(tmp_path: Path) -> None:
    dog, stalls = make_watchdog(tmp_path)
    dog.beat(now=0.0)
    dog.enter_io(now=1.0)
    dog.exit_io(now=31.0)  # a 30 s call that finally returned
    assert dog.check(now=39.0) is False  # 8 s since the exit beat: loop budget, alive
    assert dog.check(now=42.0) is True  # 11 s: now genuinely stalled
    assert "loop stall" in stalls[0]


def test_nested_windows_close_only_on_the_outermost(tmp_path: Path) -> None:
    """`exchange_agreement` pushes and then waits — one window may sit inside another;
    the inner close must not hand the loop budget back to a still-blocked call."""
    dog, _stalls = make_watchdog(tmp_path)
    dog.beat(now=0.0)
    dog.enter_io(now=1.0)
    dog.enter_io(now=2.0)
    dog.exit_io(now=3.0)
    assert dog.check(now=31.0) is False  # still inside the outer window
    dog.exit_io(now=31.0)
    assert dog.check(now=42.0) is True


def test_the_io_window_is_a_context_manager(tmp_path: Path) -> None:
    """The transport seam uses `with`, so an exception can never leave the window open."""
    dog, _stalls = make_watchdog(tmp_path)
    dog.beat(now=0.0)
    try:
        with dog.io_window():
            raise RuntimeError("transport blew up")
    except RuntimeError:
        pass
    assert dog.in_io is False
