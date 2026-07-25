"""Where the opponent listens, per sub-game (M7-11): one address or two.

Two series topologies exist in the league and both are real. The reference plays a
whole series as ONE process at ONE address; Alon's team serves TWO role-split
services, each owning the sub-games of its own role (their committed
`league_series.py`: police repo plays the odd windows, thief repo the even ones).
Our driver dialing one URL for all six sub-games is therefore wrong half the time
against a role-split opponent — the address must follow THEIR role each game.

Pure by design: resolving what the operator typed, and mapping a role to a URL,
are the two decisions a wrong guess at the T cannot repair (a peer that dials the
wrong service burns its whole connect budget before failing). Both refuse loudly
instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["SeriesEndpoints", "endpoints_from_flags", "resolve_endpoints"]


@dataclass(frozen=True)
class SeriesEndpoints:
    """The opponent's address per role they play (Input: one URL per role — equal
    for a one-address opponent; Output: the URL to dial via `for_opponent_role`)."""

    police_url: str
    thief_url: str

    def for_opponent_role(self, opponent_role: str) -> str:
        """The URL to dial for the sub-game where the OPPONENT plays `opponent_role`
        (Raises: ValueError on a role the wire does not know)."""
        if opponent_role == "police":
            return self.police_url
        if opponent_role == "thief":
            return self.thief_url
        raise ValueError(f"unknown role {opponent_role!r}: expected 'police' or 'thief'")


def resolve_endpoints(
    single: str | None = None,
    police_url: str | None = None,
    thief_url: str | None = None,
) -> SeriesEndpoints:
    """Turn what the operator provided into the series' endpoints (Input: ONE
    address for both roles, or BOTH halves of a role-split pair; blanks count as
    absent because the config default for `opponent_url` is ""; Output: the
    endpoints; Raises: ValueError on any ambiguous or incomplete combination).
    """
    one = single or None
    police = police_url or None
    thief = thief_url or None
    if one and (police or thief):
        raise ValueError(
            "give either ONE opponent address for the whole series or a "
            "police/thief pair - not both; guessing which was meant loses a series"
        )
    if one:
        return SeriesEndpoints(police_url=one, thief_url=one)
    if police and thief:
        return SeriesEndpoints(police_url=police, thief_url=thief)
    if police or thief:
        missing = "thief" if police else "police"
        raise ValueError(
            f"a role-split opponent needs BOTH addresses: the {missing} URL is missing"
        )
    raise ValueError(
        "no opponent address: give --opponent-url, or --opponent-police-url "
        "with --opponent-thief-url for a role-split opponent"
    )


def endpoints_from_flags(
    *,
    single: str | None,
    police_url: str | None,
    thief_url: str | None,
    config_default: str,
) -> SeriesEndpoints:
    """Resolve the CLI's address flags against the config fallback (Input: the three
    flags as typed plus `[network] opponent_url`; Output: the endpoints).

    The config default applies ONLY when no address flag was typed at all: it may
    name last week's opponent, and letting it collide with an explicit split pair
    would refuse a correctly-typed command for a stale reason.
    """
    if not (single or police_url or thief_url):
        single = config_default or None
    return resolve_endpoints(single=single, police_url=police_url, thief_url=thief_url)
