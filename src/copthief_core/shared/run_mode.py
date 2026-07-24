"""How a run is governed (M7-9): two axes that used to be one switch.

`counted` did two unrelated jobs at once. It armed the App F fixed rows — forcing a
genuine six-mini-game constitution, refusing any deviation — and it was also the thing
that made the lecturer addressable at all. A dress rehearsal wants the first without the
second, and could not have it: turning on the real rules also unlocked the lecturer, so
in practice nothing ever turned them on and live games ran with the rulebook disarmed.

Splitting them is only safe if the lecturer does not become EASIER to reach. Today's
protection works precisely because `counted` cannot be set casually: a counted
constitution refuses to load unless it is a real six-mini-game match. So the axes are
split, and the invariant below welds them back together in the one direction that
matters — **the lecturer needs BOTH**. `counted_series` without `strict_rules` cannot be
constructed at all, which makes the guard a property of the shape rather than of anyone
remembering to configure it correctly.

    RunMode()              dev / one-off  - rules disarmed, lecturer unreachable
    RunMode.rehearsal()    full rulebook, lecturer STRUCTURALLY unreachable
    RunMode.counted()      full rulebook, lecturer addressable
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["RunMode"]


@dataclass(frozen=True)
class RunMode:
    """The governance of one run (Input: the two axes; Raises: ValueError if a counted
    series is asked for without the rules armed)."""

    strict_rules: bool = False
    """Arm the App F fixed rows: the constitution must be a real counted-shaped match."""

    counted_series: bool = False
    """This run scores league points — the ONLY thing that may reach the lecturer."""

    def __post_init__(self) -> None:
        if self.counted_series and not self.strict_rules:
            raise ValueError(
                "a counted series must run under strict_rules: the lecturer is reachable "
                "only from a constitution the App F rows have vetted"
            )

    @property
    def lecturer_addressable(self) -> bool:
        """Whether the lecturer may appear in a recipient list at all.

        Identical to `counted_series` by construction, and named separately because the
        email layer must never be handed the RULES flag by mistake — that confusion is
        the defect this class exists to remove.
        """
        return self.counted_series

    @classmethod
    def rehearsal(cls) -> RunMode:
        """A friendly played exactly like a counted game, minus the counting: the full
        rulebook enforced, and no arrangement of recipients can reach the lecturer."""
        return cls(strict_rules=True, counted_series=False)

    @classmethod
    def counted(cls) -> RunMode:
        """A real counted series: full rulebook, lecturer addressable."""
        return cls(strict_rules=True, counted_series=True)
