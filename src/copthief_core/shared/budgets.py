"""Timing-budget reconciliation (M7-7(1)): the ordering is asserted, not assumed.

The real-tunnel kill drill lost a game to two budgets that had never been related to
each other anywhere: the SIGNED `watchdog_timeout_sec` (60, App F `network_and_league`)
and the private `turn_timeout_seconds` (180). At runtime the wrong one won and we
self-terminated. The relationship is stated here, once, and enforced at config load —
a tree that would kill us refuses to load instead of losing a counted game.

The four rules, in the order they bite:

1. `watchdog_timeout_sec > 0` — an armed watchdog with no budget is not armed.
2. `poll_interval_seconds < watchdog_timeout_sec` — an idle loop beats once per poll,
   so a poll that can outlast the loop budget self-terminates a healthy waiting peer.
3. `connect_timeout_seconds <= turn_timeout_seconds` — an outbound give-up must never
   outlast our own rule budget, or the transport abandons a peer the deadline still
   considers in-budget.
4. `io_stall_timeout > turn_timeout_seconds` — the blocker itself: whatever a stalled
   transport does, OUR OWN turn deadline expires first, so a silent opponent is
   classified by rule (technical loss, App E) and never by suicide.
5. `inbound_buffer_limit >= 1` (M7-8) — a receiver with no reorder window turns an
   at-least-once retry race into a protocol violation; zero tolerance is not a
   tightening here, it is a self-inflicted technical loss.
6. `call_timeout_seconds < response_timeout_sec` (M7-57) — ONE outbound call must end
   well inside the deadline the opponent is entitled to enforce. Every budget above
   bounds an exchange; none bounds a single delivered-but-unanswered push, so that
   push inherited the transport library's own default. In the 2026-08-09 friendly two
   of those hidden waits plus a retry put our turn on the wire 61.0 s after the
   opponent's — inside a signed 30 s budget. A deadline nobody chose is a deadline
   nobody reconciled.

Nothing here changes a signed value: rule 4 is satisfied by making the I/O budget
*derived* (turn budget + the signed watchdog budget as grace), which is why the fix is
semantics rather than a config bump — App F guard untouched.
"""

from __future__ import annotations

from copthief_core.shared.config_model import Constitution, PrivateSettings
from copthief_core.shared.private_config import ConfigError


def io_stall_timeout(constitution: Constitution, private: PrivateSettings) -> float:
    """The budget for a loop deliberately blocked in the transport (Input: the loaded
    config pair; Output: seconds). Sits behind the turn deadline by exactly the signed
    watchdog budget, so the ordering of rule 4 holds by construction."""
    return private.turn_timeout_seconds + constitution.league.watchdog_timeout_sec


def reconcile_budgets(constitution: Constitution, private: PrivateSettings) -> None:
    """Assert the loop / turn / transport budgets are ordered (Input: the loaded config
    pair; Output: none; Raises: ConfigError listing EVERY violation at once — the App F
    guard's habit, because a config is fixed in one pass or not at all)."""
    watchdog = constitution.league.watchdog_timeout_sec
    turn, poll = private.turn_timeout_seconds, private.poll_interval_seconds
    connect = private.connect_timeout_seconds
    problems: list[str] = []
    if watchdog <= 0:
        problems.append(f"watchdog_timeout_sec must be positive, got {watchdog}")
    if poll >= watchdog:
        problems.append(
            f"poll_interval_seconds ({poll}) must be under watchdog_timeout_sec "
            f"({watchdog}): an idle loop beats once per poll"
        )
    if connect > turn:
        problems.append(
            f"connect_timeout_seconds ({connect}) must not exceed turn_timeout_seconds "
            f"({turn}): an outbound give-up may not outlast our own rule budget"
        )
    if io_stall_timeout(constitution, private) <= turn:
        problems.append(
            f"the I/O stall budget must sit strictly behind turn_timeout_seconds ({turn})"
        )
    if private.inbound_buffer_limit < 1:
        problems.append(
            f"inbound_buffer_limit ({private.inbound_buffer_limit}) must be at least 1: "
            "at-least-once delivery can put two of the opponent's pushes in flight"
        )
    response = constitution.league.response_timeout_sec
    if private.call_timeout_seconds >= response:
        problems.append(
            f"call_timeout_seconds ({private.call_timeout_seconds}) must be under the signed "
            f"response_timeout_sec ({response}): one delivered-but-unanswered push may not "
            "outlast the deadline the opponent enforces, or no retry fits inside it"
        )
    if problems:
        raise ConfigError("timing budgets are not reconciled:\n" + "\n".join(problems))
