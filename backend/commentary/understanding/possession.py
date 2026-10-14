"""
Phase 2: Possession Tracking.
Segments continuous simulation steps into team possession intervals and turnover boundaries.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class PossessionInterval:
    team_idx: int  # 0 = home, 1 = away, -1 = loose
    team_name: str
    start_step: int
    end_step: int
    duration_steps: int
    event_ids: List[str]


class PossessionTracker:
    """Tracks possession stretches and turnovers across match steps."""

    def __init__(self, home_team: str = "Burnley", away_team: str = "Bournemouth"):
        self.home_team = home_team
        self.away_team = away_team

    def segment_possessions(
        self,
        ball_owned_team: List[int],
        events_by_step: Dict[int, List[str]],
    ) -> List[PossessionInterval]:
        intervals: List[PossessionInterval] = []
        if not len(ball_owned_team):
            return intervals

        curr_team = int(ball_owned_team[0])
        start_step = 0
        curr_evts: List[str] = list(events_by_step.get(0, []))

        for step in range(1, len(ball_owned_team)):
            t = int(ball_owned_team[step])
            if step in events_by_step:
                curr_evts.extend(events_by_step[step])

            # Transition when team ownership explicitly switches between teams
            # (ignoring momentary -1 loose ball frames unless prolonged)
            if t >= 0 and t != curr_team and curr_team >= 0:
                team_name = self.home_team if curr_team == 0 else self.away_team
                intervals.append(
                    PossessionInterval(
                        team_idx=curr_team,
                        team_name=team_name,
                        start_step=start_step,
                        end_step=step - 1,
                        duration_steps=(step - start_step),
                        event_ids=curr_evts,
                    )
                )
                curr_team = t
                start_step = step
                curr_evts = []
            elif curr_team < 0 and t >= 0:
                curr_team = t
                start_step = step

        # Final interval
        if curr_team >= 0 and start_step < len(ball_owned_team):
            team_name = self.home_team if curr_team == 0 else self.away_team
            intervals.append(
                PossessionInterval(
                    team_idx=curr_team,
                    team_name=team_name,
                    start_step=start_step,
                    end_step=len(ball_owned_team) - 1,
                    duration_steps=len(ball_owned_team) - start_step,
                    event_ids=curr_evts,
                )
            )

        return intervals
