"""Which sub-game index the next window opens on (M7-43) — pure, no I/O.

The uoh-sqak friendly (2026-08-06) was lost to index drift, and the drift was
ASYMMETRIC, which is what makes this more than a retry counter. Their peer accepted our
agreement and entered sub-game 2; ours never saw their reply and logged no contact at
all. They timed out — a settlement, so they advanced — while we saw no game at all. Our
driver then advanced unconditionally (`for n in range(...)`), so one lost push put us
three indices ahead and the pairing guard correctly refused every later window.

Two rules, and BOTH are needed:

- **Hold on a failed handshake.** A window where no game happened must not consume an
  index. This is the rule uoh-sqak already implements and we did not.
- **Catch up to a peer that is strictly ahead.** Hold-only fixes symmetric failures and
  INVERTS asymmetric ones: had both sides only held, we would have sat on 2 while they
  settled onward, deadlocked on different numbers. A higher declared index means they
  have settled windows we cannot un-play; those sub-games are lost, the series is not.

Catch-up is **monotonic** on purpose: we follow a peer forward, never backward. If both
peers could move either way they would ping-pong, and a peer that is behind can catch up
to us by this same rule. A declared index beyond the signed `num_games` is ignored
outright — confused or hostile, never followed.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["HANDSHAKE_FAILED", "Pacing", "became_a_game", "declared_index", "next_window"]

# The outcome a window reports when NO GAME HAPPENED — the handshake never completed.
# Distinct from `timeout`, which is a settled technical loss: the game existed, it is
# scored, and its index is spent. Conflating the two is what makes a retry rule unsafe.
HANDSHAKE_FAILED = "handshake_failed"

# Outcomes that are only a SETTLEMENT if turns were actually exchanged (uoh-sqak's
# refinement, 2026-08-06). Their sub-game 2 completed a handshake and then timed out at
# zero turns; a bare settlement reading advances on that, so they spent the index while
# we held it — the drift opened with BOTH sides obeying the rule we had just agreed.
# From the other peer's side an empty window is indistinguishable from a handshake that
# never landed, so it must be treated the same way. A technical loss WITH play behind it
# still settles: it has a result, it is scored, and replaying a decided sub-game is
# worse than the drift.
NO_PLAY_OUTCOMES = frozenset({"timeout", "unknown", HANDSHAKE_FAILED})


def became_a_game(outcome: str, steps: int) -> bool:
    """Did this window actually produce a game? (Input: the reported outcome and turn
    count; Output: False when nothing was played and the index must be held.)"""
    return outcome not in NO_PLAY_OUTCOMES or steps > 0


@dataclass(frozen=True)
class Pacing:
    """The next window's index, the retries spent on it, and whether to give up."""

    index: int
    retries_used: int
    stop: bool


def handshake_failed_result(why: str, peer_sub_game: int | None) -> dict[str, object]:
    """The result a peer prints when NO GAME HAPPENED (Input: the refusal reason and the
    index the opponent declared, if any; Output: the window result dict).

    Lives beside the rules rather than in the CLI because it IS the pacing contract's
    wire shape: `declared_index` reads back exactly what this writes.
    """
    return {
        "outcome": HANDSHAKE_FAILED,
        "steps": 0,
        "audit_ok": False,
        "why": why,
        "peer_sub_game": peer_sub_game,
    }


def declared_index(result: dict[str, object]) -> int | None:
    """The sub-game index the opponent declared while refusing us, if any (Input: one
    window's result dict; Output: the index, or None when they never spoke).

    A bool is not an index: `True` is an `int` in Python and would read as sub-game 1.
    """
    value = result.get("peer_sub_game")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def next_window(
    *,
    current: int,
    outcome: str,
    steps: int,
    peer_declared: int | None,
    retries_used: int,
    retry_budget: int,
    num_games: int,
) -> Pacing:
    """Decide the next window (Input: the window just finished, how many turns it
    exchanged, what the opponent declared while refusing, and the retry budget; Output:
    the next `Pacing`).

    `peer_declared` is the highest sub-game index the opponent declared during a refused
    handshake, or None if they never spoke.
    """
    if became_a_game(outcome, steps):
        # A settled window spends its index even if the peer declared something higher:
        # we hold a real result for THIS sub-game and must not skip reporting it.
        return Pacing(index=current + 1, retries_used=0, stop=False)
    if peer_declared is not None and current < peer_declared <= num_games:
        return Pacing(index=peer_declared, retries_used=0, stop=False)
    if retries_used + 1 > retry_budget:
        return Pacing(index=current, retries_used=retries_used, stop=True)
    return Pacing(index=current, retries_used=retries_used + 1, stop=False)
