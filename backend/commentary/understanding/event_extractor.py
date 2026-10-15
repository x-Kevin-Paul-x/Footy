"""
Phase 1: Deterministic Football Event Extractor.
Extracts factual football events from simulation arrays and authoritative manifest events.
Only extracts event types verified by Phase -1 capabilities report.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from backend.commentary.schemas import EnrichedEvent
from backend.commentary.understanding.timeline_adapter import TimelineAdapter
from backend.commentary.config import (
    PENALTY_BOX_X_HOME,
    PENALTY_BOX_X_AWAY,
    PENALTY_BOX_Y_HALF_WIDTH,
)


class EventExtractor:
    """Extracts ground-truth football events from simulation trajectory and manifest."""

    def __init__(self, trace_npz_path: Path, timeline_adapter: TimelineAdapter):
        self.npz_path = trace_npz_path
        self.timeline = timeline_adapter

        loaded = np.load(trace_npz_path, allow_pickle=False)
        self.player_coords = loaded["player_coords"]  # (N, 22, 2)
        self.ball_coords = loaded["ball_coords"]      # (N, 3)
        self.ball_dirs = loaded['ball_dirs']
        self.ball_owned_team = loaded["ball_owned_team"]  # (N,)
        self.ball_owned_player = loaded["ball_owned_player"]  # (N,)
        self.actions = loaded['actions']
        self.game_mode = loaded['game_mode']
        self.total_steps = len(self.ball_coords)

        manifest_raw = loaded["manifest"][0]
        self.manifest = json.loads(str(manifest_raw)) if isinstance(manifest_raw, (str, np.str_)) else manifest_raw

        self.home_team = self.manifest.get("home_team", "Burnley")
        self.away_team = self.manifest.get("away_team", "Bournemouth")
        self.home_players = self.manifest.get("home_players", [])
        self.away_players = self.manifest.get("away_players", [])
        self.canonical_events = self.manifest.get("events", [])

    def get_player_name(self, team_idx: int, player_idx: int) -> str:
        """Resolve team and player index (0-10) to real name."""
        if team_idx == 0 and 0 <= player_idx < len(self.home_players):
            return self.home_players[player_idx]
        elif team_idx == 1 and 0 <= player_idx < len(self.away_players):
            return self.away_players[player_idx]
        return "Unknown Player"

    def get_team_name(self, team_idx: int) -> str:
        if team_idx == 0:
            return self.home_team
        elif team_idx == 1:
            return self.away_team
        return "Neutral"

    def extract_events(self) -> List[EnrichedEvent]:
        """Extract all verified events in chronological order."""
        events: List[EnrichedEvent] = []
        event_counter = 0

        # Step 1: Map all canonical events from manifest (shots, goals, hit_post, cards, halftime, fulltime)
        canonical_step_map: Dict[int, List[Dict[str, Any]]] = {}
        for ce in self.canonical_events:
            st = int(ce.get("step", 0))
            canonical_step_map.setdefault(st, []).append(ce)

        # Step 2: Track possession states, passes, carries, and box entries across simulation steps
        prev_owner_team = -1
        prev_owner_player = -1
        possession_start_step = 0
        carry_start_step = 0
        carry_start_pos = None

        in_home_box = False
        in_away_box = False

        for step in range(self.total_steps):
            bx, by, bz = self.ball_coords[step]
            curr_team = int(self.ball_owned_team[step])
            curr_player = int(self.ball_owned_player[step])
            pts_ms = self.timeline.step_to_ms(step, self.total_steps)
            minute = max(1, min(90, int(step / (self.total_steps / 90.0)) + 1))
            new_control = step == 0 or (curr_team != int(self.ball_owned_team[step-1]) or curr_player != int(self.ball_owned_player[step-1]))
            attacking_x = float(bx) * (1 if curr_team == 0 else -1)
            if curr_team >= 0 and curr_player >= 0 and int(self.game_mode[step]) == 0 and attacking_x > .55 and (step % 5 == 0 or new_control):
                event_counter += 1
                events.append(EnrichedEvent(event_id=f'evt_{event_counter:04d}', type='CONTROL_IN_ATTACK',
                    step=step, presentation_ms=pts_ms, match_minute=minute,
                    team=self.get_team_name(curr_team), player=self.get_player_name(curr_team, curr_player),
                    position=[float(bx), float(by)], facts={'source':'recorded_possession'}))

            # --- Check Canonical Manifest Events First ---
            if step in canonical_step_map:
                for ce in canonical_step_map[step]:
                    ce_type = ce.get("type", "").lower()
                    team_str = self.home_team if ce.get("team") == "home" else self.away_team
                    player_name = ce.get("player") or ce.get("scorer") or ""
                    xg_val = float(ce.get("xg", 0.0))

                    if ce_type == "shot":
                        event_counter += 1
                        events.append(
                            EnrichedEvent(
                                event_id=f"evt_{event_counter:04d}",
                                type="SHOT",
                                step=step,
                                presentation_ms=pts_ms,
                                match_minute=int(ce.get('minute', minute)),
                                team=team_str,
                                player=player_name,
                                position=[round(float(bx), 3), round(float(by), 3)],
                                importance=0.85 if ce.get("outcome") == "GOAL" else 0.65,
                                danger=min(1.0, 0.70 + xg_val),
                                facts={
                                    "xg": float(xg_val),
                                    "on_target": bool(ce.get("on_target", True)),
                                    "outcome": str(ce.get("outcome", "SHOT")),
                                },
                            )
                        )
                    elif ce_type == "goal":
                        event_counter += 1
                        events.append(
                            EnrichedEvent(
                                event_id=f"evt_{event_counter:04d}",
                                type="GOAL",
                                step=step,
                                presentation_ms=pts_ms,
                                match_minute=int(ce.get('minute', minute)),
                                team=team_str,
                                player=player_name,
                                position=[round(float(bx), 3), round(float(by), 3)],
                                importance=1.00,
                                danger=1.00,
                                facts={
                                    "scorer": player_name,
                                    "score": ce.get("score", ""),
                                },
                            )
                        )
                    elif ce_type == "hit_post":
                        event_counter += 1
                        events.append(
                            EnrichedEvent(
                                event_id=f"evt_{event_counter:04d}",
                                type="HIT_POST",
                                step=step,
                                presentation_ms=pts_ms,
                                match_minute=minute,
                                team=team_str,
                                player=player_name,
                                position=[round(float(bx), 3), round(float(by), 3)],
                                importance=0.88,
                                danger=0.92,
                                facts={"player": player_name},
                            )
                        )
                    elif ce_type == "half_time":
                        event_counter += 1
                        events.append(
                            EnrichedEvent(
                                event_id=f"evt_{event_counter:04d}",
                                type="HALFTIME",
                                step=step,
                                presentation_ms=pts_ms,
                                match_minute=45,
                                team="Neutral",
                                player="",
                                position=[0.0, 0.0],
                                importance=0.70,
                                danger=0.0,
                                facts={"score": ce.get("score", "")},
                            )
                        )
                    elif ce_type == "full_time":
                        event_counter += 1
                        events.append(
                            EnrichedEvent(
                                event_id=f"evt_{event_counter:04d}",
                                type="FULLTIME",
                                step=step,
                                presentation_ms=pts_ms,
                                match_minute=90,
                                team="Neutral",
                                player="",
                                position=[0.0, 0.0],
                                importance=0.95,
                                danger=0.0,
                                facts={"score": ce.get("score", "")},
                            )
                        )

            # --- Check Box Entries ---
            in_h_box_now = (bx <= PENALTY_BOX_X_HOME) and (abs(by) <= PENALTY_BOX_Y_HALF_WIDTH)
            in_a_box_now = (bx >= PENALTY_BOX_X_AWAY) and (abs(by) <= PENALTY_BOX_Y_HALF_WIDTH)

            if in_h_box_now and not in_home_box and curr_team == 1:  # Away team enters home box
                event_counter += 1
                events.append(
                    EnrichedEvent(
                        event_id=f"evt_{event_counter:04d}",
                        type="BOX_ENTRY",
                        step=step,
                        presentation_ms=pts_ms,
                        match_minute=minute,
                        team=self.away_team,
                        player=self.get_player_name(curr_team, curr_player) if curr_player >= 0 else "",
                        position=[round(float(bx), 3), round(float(by), 3)],
                        importance=0.75,
                        danger=0.80,
                        facts={"box": f"{self.home_team} penalty area", "entered_from": "center" if abs(by) < 0.1 else ("right" if by > 0 else "left")},
                    )
                )
            if in_a_box_now and not in_away_box and curr_team == 0:  # Home team enters away box
                event_counter += 1
                events.append(
                    EnrichedEvent(
                        event_id=f"evt_{event_counter:04d}",
                        type="BOX_ENTRY",
                        step=step,
                        presentation_ms=pts_ms,
                        match_minute=minute,
                        team=self.home_team,
                        player=self.get_player_name(curr_team, curr_player) if curr_player >= 0 else "",
                        position=[round(float(bx), 3), round(float(by), 3)],
                        importance=0.75,
                        danger=0.80,
                        facts={"box": f"{self.away_team} penalty area", "entered_from": "center" if abs(by) < 0.1 else ("right" if by > 0 else "left")},
                    )
                )
            in_home_box = in_h_box_now
            in_away_box = in_a_box_now

            # --- Track Passes & Carries & Turnovers ---
            if int(self.game_mode[step]) != 0:
                prev_owner_team = prev_owner_player = -1
                continue
            if curr_team >= 0 and curr_player >= 0:
                if prev_owner_team >= 0 and prev_owner_player >= 0:
                    # Same team, different player = Pass Completed
                    if curr_team == prev_owner_team and curr_player != prev_owner_player:
                        p1_name = self.get_player_name(prev_owner_team, prev_owner_player)
                        p2_name = self.get_player_name(curr_team, curr_player)
                        t_name = self.get_team_name(curr_team)

                        # Check progression
                        prev_x = self.ball_coords[carry_start_step][0] if carry_start_step < self.total_steps else bx
                        dx = (bx - prev_x) if curr_team == 0 else (prev_x - bx)
                        is_progressive = bool(dx > 0.15)

                        event_counter += 1
                        events.append(
                            EnrichedEvent(
                                event_id=f"evt_{event_counter:04d}",
                                type="PROGRESSIVE_PASS" if is_progressive else "PASS",
                                step=step,
                                presentation_ms=pts_ms,
                                match_minute=minute,
                                team=t_name,
                                player=p1_name,
                                position=[round(float(bx), 3), round(float(by), 3)],
                                importance=0.45 if is_progressive else 0.25,
                                danger=0.55 if is_progressive else 0.25,
                                facts={
                                    "passer": p1_name,
                                    "receiver": p2_name,
                                    "progressive": is_progressive,
                                },
                            )
                        )
                        carry_start_step = step
                        carry_start_pos = (bx, by)

                    # Different team = Turnover
                    elif curr_team != prev_owner_team:
                        lost_team = self.get_team_name(prev_owner_team)
                        won_team = self.get_team_name(curr_team)
                        winner_name = self.get_player_name(curr_team, curr_player)
                        event_counter += 1
                        events.append(
                            EnrichedEvent(
                                event_id=f"evt_{event_counter:04d}",
                                type="TURNOVER",
                                step=step,
                                presentation_ms=pts_ms,
                                match_minute=minute,
                                team=won_team,
                                player=winner_name,
                                position=[round(float(bx), 3), round(float(by), 3)],
                                importance=0.50,
                                danger=0.45,
                                facts={"lost_by": lost_team, "won_by": won_team, "player": winner_name},
                            )
                        )
                        carry_start_step = step
                        carry_start_pos = (bx, by)

                else:
                    # Gained possession from loose ball
                    t_name = self.get_team_name(curr_team)
                    p_name = self.get_player_name(curr_team, curr_player)
                    event_counter += 1
                    events.append(
                        EnrichedEvent(
                            event_id=f"evt_{event_counter:04d}",
                            type="POSSESSION_START",
                            step=step,
                            presentation_ms=pts_ms,
                            match_minute=minute,
                            team=t_name,
                            player=p_name,
                            position=[round(float(bx), 3), round(float(by), 3)],
                            importance=0.20,
                            danger=0.20,
                            facts={"player": p_name, "team": t_name},
                        )
                    )
                    carry_start_step = step
                    carry_start_pos = (bx, by)

                prev_owner_team = curr_team
                prev_owner_player = curr_player

        # A recorded release is a shot attempt, never advance knowledge of its
        # outcome. Canonical "shot" events sometimes share the goal's step.
        releases = []
        for step in range(1, self.total_steps):
            team = int(self.ball_owned_team[step - 1])
            player = int(self.ball_owned_player[step - 1])
            if int(self.game_mode[step - 1]) != 0:
                continue
            action_index = team * 10 + player - 1
            explicit = team >= 0 and player >= 1 and action_index < self.actions.shape[1] and int(self.actions[step - 1, action_index]) == 12
            # Built-in AI action 19 hides individual kicks. Infer a dangerous
            # release from observed acceleration and goalward travel only.
            velocity = self.ball_dirs[step, :2]
            previous = self.ball_dirs[step - 1, :2]
            bx, by = self.ball_coords[step, :2]
            inferred = (int(self.ball_owned_team[step]) == -1 and abs(bx) > .55
                        and bx * velocity[0] > 0 and abs(velocity[0]) > .035
                        and np.linalg.norm(velocity - previous) > .025)
            if inferred:
                goal_x = 1 if velocity[0] > 0 else -1
                projected_y = by + (goal_x - bx) * velocity[1] / velocity[0]
                inferred = abs(projected_y) < .15
            if not explicit and not inferred:
                continue
            if inferred and team < 0:
                team = 0 if velocity[0] > 0 else 1
                # A volley with no recorded owner cannot safely name a shooter.
                player = -1
            if releases and releases[-1].team == self.get_team_name(team) and step - releases[-1].step < 12:
                continue
            event_counter += 1
            releases.append(EnrichedEvent(
                event_id=f'evt_{event_counter:04d}', type='SHOT_RELEASE', step=step,
                presentation_ms=self.timeline.step_to_ms(step, self.total_steps),
                match_minute=self.timeline.pts_to_match_minute(self.timeline.step_to_pts(step)),
                team=self.get_team_name(team), player=self.get_player_name(team, player) if player >= 0 else '',
                position=self.ball_coords[step - 1].tolist(), importance=0.85, danger=0.9,
                facts={'source': 'recorded_shot_action' if explicit else 'observed_goalward_acceleration',
                       'inferred': not explicit, 'outcome': 'UNRESOLVED'}))
        events.extend(releases)
        for event in events:
            if event.type == 'GOAL':
                attempts = [a for a in releases if a.team == event.team and a.player in ('', event.player) and 0 < event.step - a.step <= 60]
                if attempts:
                    event.facts['shot_release_ms'] = attempts[-1].presentation_ms
        # Keep speech knowledge chronological, including shots before goals.
        events.sort(key=lambda e: (e.presentation_ms, e.type == 'GOAL', -e.importance))
        from backend.commentary.understanding.danger import DangerEngine
        danger_engine = DangerEngine()
        score = (0, 0)
        for event in events:
            if event.type == 'GOAL':
                score = tuple(int(n) for n in event.facts['score'].split('-'))
            team_idx = 0 if event.team == self.home_team else 1 if event.team == self.away_team else -1
            if team_idx < 0:
                continue
            components = danger_engine.evaluate_step(event.step, self.ball_coords[event.step],
                self.ball_dirs[event.step], team_idx, self.player_coords[event.step],
                xg_val=float(event.facts.get('xg', 0)), is_goal=event.type == 'GOAL',
                minute=event.match_minute, score_diff=score[0]-score[1])
            event.danger = components.composite_danger
            event.importance = max(event.importance, components.importance)
            event.facts['danger_components'] = components.model_dump()
        return events
