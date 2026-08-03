"""League-standing facts for the final result (M7-34), split from report/emit
(150-line rule). Book §9.2.1 + the attached example's `4-final-result` fields."""

from __future__ import annotations

from typing import Any


def league_facts(
    own_identity: dict[str, Any],
    opponent_identity: dict[str, Any],
    aggregate: dict[str, Any],
    *,
    counted: bool,
    first_meeting: bool,
) -> dict[str, Any]:
    """The final_result league fields (book §9.2.1 + the attached example).

    Counts come from each side's OWN declaration (`counted_games_played` — the
    rules-37/38 mutual declarations the diversity weighting reads); an opponent that
    declared none counts from 0, the honest floor. The diversity reward goes to the
    WINNER of a counted FIRST meeting only ("ניקוד על ניצחון מול יריבה חדשה", App F);
    a warm-up never counts and never rewards. Deliberately OUTSIDE the signed
    symmetric outcome: the two sides' declared counts are their own claims, not
    shared game facts.
    """
    own_gid, opp_gid = own_identity["group_id"], opponent_identity["group_id"]
    bump = 1 if counted else 0
    opp_declared = opponent_identity.get("counted_games_played")
    winner = aggregate.get("winner_group")
    return {
        "games_played_including_this": {
            own_gid: int(own_identity.get("counted_games_played", 0) or 0) + bump,
            opp_gid: (int(opp_declared) if opp_declared is not None else 0) + bump,
        },
        "first_meeting_between_groups": first_meeting,
        "diversity_reward_applied": {
            gid: bool(counted and first_meeting and winner == gid) for gid in (own_gid, opp_gid)
        },
    }
