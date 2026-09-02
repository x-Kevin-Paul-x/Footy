"""
Footy Simulation Worker: Isolated Single-Match GRF Execution Unit.
Encapsulates 11v11 GRF physics, tactical modulation, canonical feature extraction,
preallocated trajectory recording, and state archiving.
"""

import os
import sys
import time
import enum
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

import gym
import gfootball.env as football_env

from logic.grf_trajectory import MatchTrajectory, MatchManifest
from logic.grf_state_archive import GRFStateArchiveWriter, ReplayIntegrityError
from logic.replay_schema import SIM_STEP_SECONDS
from logic.grf_core import (
    extract_canonical_features,
    compute_shot_xg,
    apply_tactical_action_bias,
    ACTION_MIRROR_MAP
)
from logic.footy_grf_adapter import (
    FootyGRFAdapter,
    FORMATION_COORDINATES,
    GRFPlayerProfile,
    GRFTeamTactics
)


class ReplayMode(enum.Enum):
    NONE = "none"              # Fastest: only compute match result/stats, skip trajectory recording
    TRAJECTORY = "trajectory"  # Standard: record 2D player/ball coordinates & events for analytics
    FULL_STATE = "full_state"  # Broadcast: record full C++ engine state bytes to .grfstate archive


class SimulationWorker:
    """
    Self-contained simulation worker that executes an isolated 11v11 GRF match.
    Owns its environment, tactics, trajectory buffers, and state archive writer.
    """

    def __init__(self, fixture: Dict[str, Any], max_steps: int = 1200, replay_mode: ReplayMode = ReplayMode.FULL_STATE):
        self.fixture = fixture
        self.max_steps = max_steps
        self.replay_mode = replay_mode
        self.match_id = str(fixture["match_id"])

        # Deterministic seed resolution
        seed_val = fixture.get("seed_val")
        if seed_val is None:
            self.seed_val = int.from_bytes(hashlib.sha256(f"match_{self.match_id}".encode()).digest()[:4], "little")
        else:
            self.seed_val = int(seed_val)

        import random
        import torch
        seed_32 = self.seed_val % (2**31 - 1)
        np.random.seed(seed_32)
        random.seed(seed_32)
        torch.manual_seed(seed_32)

        # Team identity & tactics setup
        self.home_team = fixture.get("home_team", "Home Team")
        self.away_team = fixture.get("away_team", "Away Team")
        self.home_players = fixture.get("home_players") or [f"{self.home_team} Player {i+1}" for i in range(11)]
        self.away_players = fixture.get("away_players") or [f"{self.away_team} Player {i+1}" for i in range(11)]
        self.home_formation = fixture.get("home_formation", "4-3-3")
        self.away_formation = fixture.get("away_formation", "4-2-3-1")

        raw_h_profiles = fixture.get("home_profiles")
        if raw_h_profiles and isinstance(raw_h_profiles, list):
            h_roster = [GRFPlayerProfile(**p) if isinstance(p, dict) else p for p in raw_h_profiles]
        else:
            h_roster = [FootyGRFAdapter.extract_player_profile(p, assigned_pos="GK" if i == 0 else "CM")
                        for i, p in enumerate(self.home_players[:11])]

        raw_a_profiles = fixture.get("away_profiles")
        if raw_a_profiles and isinstance(raw_a_profiles, list):
            a_roster = [GRFPlayerProfile(**p) if isinstance(p, dict) else p for p in raw_a_profiles]
        else:
            a_roster = [FootyGRFAdapter.extract_player_profile(p, assigned_pos="GK" if i == 0 else "CM")
                        for i, p in enumerate(self.away_players[:11])]

        self.home_tactics = GRFTeamTactics(
            team_name=self.home_team,
            formation=self.home_formation if self.home_formation in FORMATION_COORDINATES else "4-3-3",
            offensive_bias=float(fixture.get("home_offensive_bias", 50.0)),
            defensive_bias=float(fixture.get("home_defensive_bias", 50.0)),
            pressing_intensity=float(fixture.get("home_pressing_intensity", 50.0)),
            tempo=float(fixture.get("home_tempo", 50.0)),
            roster=h_roster
        )
        self.away_tactics = GRFTeamTactics(
            team_name=self.away_team,
            formation=self.away_formation if self.away_formation in FORMATION_COORDINATES else "4-2-3-1",
            offensive_bias=float(fixture.get("away_offensive_bias", 50.0)),
            defensive_bias=float(fixture.get("away_defensive_bias", 50.0)),
            pressing_intensity=float(fixture.get("away_pressing_intensity", 50.0)),
            tempo=float(fixture.get("away_tempo", 50.0)),
            roster=a_roster
        )

        self.home_anchors = self.home_tactics.get_formation_anchors(is_right_team=False)[1:]
        self.away_anchors = self.away_tactics.get_formation_anchors(is_right_team=True)[1:]

        self.home_color = fixture.get("home_color", "#e63946")
        self.away_color = fixture.get("away_color", "#2196f3")
        self.trace_npz = fixture.get("trace_npz") or fixture.get("trajectory_file")
        self.states_file = fixture.get("states_file")

        # Dump recording setup
        dump_path = fixture.get("trace_dump")
        self.record_dump = bool(dump_path or fixture.get("record_dump", False))
        self.match_dump_dir = f"/tmp/dumps/worker_{self.match_id}_{int(time.time()*1000)%100000}"
        if self.record_dump:
            os.makedirs(self.match_dump_dir, exist_ok=True)

        # Canonical feature trackers
        self.left_loff = np.zeros(11, dtype=np.float32)
        self.left_roff = np.zeros(11, dtype=np.float32)
        self.right_loff = np.zeros(11, dtype=np.float32)
        self.right_roff = np.zeros(11, dtype=np.float32)

        # Preallocated trajectory recording buffers
        if self.replay_mode in (ReplayMode.TRAJECTORY, ReplayMode.FULL_STATE):
            self.rec_players = np.empty((self.max_steps, 22, 2), dtype=np.float32)
            self.rec_player_dirs = np.empty((self.max_steps, 22, 2), dtype=np.float32)
            self.rec_balls = np.empty((self.max_steps, 3), dtype=np.float32)
            self.rec_ball_dirs = np.empty((self.max_steps, 3), dtype=np.float32)
            self.rec_actions = np.empty((self.max_steps, 20), dtype=np.uint8)
            self.rec_scores = np.empty((self.max_steps, 2), dtype=np.uint8)
            self.rec_game_modes = np.empty(self.max_steps, dtype=np.int8)
            self.rec_owned_teams = np.empty(self.max_steps, dtype=np.int8)
            self.rec_owned_players = np.empty(self.max_steps, dtype=np.int8)
        else:
            self.rec_players = None

        # State Archive Writer setup
        self.archive_writer = None
        if self.replay_mode == ReplayMode.FULL_STATE and self.states_file:
            self.archive_writer = GRFStateArchiveWriter(self.states_file, self.match_id)

        # Match statistics & state machines
        self.step_idx = 0
        self.done = False
        self.actual_steps = None
        self.curr_score = [0, 0]
        self.last_score = [0, 0]
        self.left_poss = 0
        self.right_poss = 0
        self.shots_h = 0
        self.shots_a = 0
        self.sot_h = 0
        self.sot_a = 0
        self.xg_h = 0.0
        self.xg_a = 0.0
        self.passes_h_att = 0
        self.passes_h_cmp = 0
        self.passes_a_att = 0
        self.passes_a_cmp = 0
        self.last_home_touch = 10
        self.last_away_touch = 10
        self.active_pass = None
        self.active_shot = None
        self.events = []

        # C++ GRF Environment instantiation
        other_opts = {
            'action_set': 'full',
            'random_seed': self.seed_val % (2**31 - 1),
        }
        if self.record_dump:
            other_opts['tracesdir'] = self.match_dump_dir
            other_opts['dump_full_episodes'] = True

        self.env = football_env.create_environment(
            env_name="11_vs_11_kaggle",
            stacked=False,
            representation='raw',
            rewards='scoring',
            write_goal_dumps=False,
            write_full_episode_dumps=self.record_dump,
            render=False,
            number_of_left_players_agent_controls=10,
            number_of_right_players_agent_controls=10,
            other_config_options=other_opts
        )
        self.raw_obs = self.env.reset()

    def get_initial_observations(self) -> np.ndarray:
        """Extracts canonical 268-dim features for the 20 outfield agents (10 home, 10 away)."""
        obs_l, self.left_loff, self.left_roff = extract_canonical_features(
            self.raw_obs[0:10], team_side="left", num_agents=10,
            last_loff=self.left_loff, last_roff=self.left_roff
        )
        obs_r, self.right_loff, self.right_roff = extract_canonical_features(
            self.raw_obs[10:20], team_side="right", num_agents=10,
            last_loff=self.right_loff, last_roff=self.right_roff
        )
        return np.concatenate([obs_l, obs_r], axis=0)  # Shape: (20, 268)

    def step(self, raw_actions: np.ndarray) -> Tuple[np.ndarray, bool, Dict[str, Any]]:
        """
        Executes one simulation tick:
        1. Modulates 20 raw actions with tactical bias and mirroring.
        2. Steps C++ GRF environment.
        3. Records trajectory frame & state bytes.
        4. Updates state machines (xG, passes, shots, score, half-time, goals).
        5. Extracts next 20 canonical observations.
        """
        if self.done or self.step_idx >= self.max_steps:
            return np.zeros((20, 268), dtype=np.float32), True, {}

        l_act_raw = raw_actions[0:10].tolist()
        r_act_raw = raw_actions[10:20].tolist()

        o_prev = self.raw_obs[0]
        ball_xy = np.array(o_prev['ball'][:2], dtype=np.float32)
        b_own_prev = o_prev.get('ball_owned_team', -1)
        l_pos = np.array(o_prev['left_team'][1:], dtype=np.float32)
        r_pos = np.array(o_prev['right_team'][1:], dtype=np.float32)

        # Tactical modulation
        l_act = apply_tactical_action_bias(
            l_act_raw, l_pos, self.home_anchors, self.home_tactics,
            team_side="left", ball_xy=ball_xy, is_team_in_possession=(b_own_prev == 0)
        )
        r_act_tactical = apply_tactical_action_bias(
            r_act_raw, -r_pos, [(-x, -y) for (x, y) in self.away_anchors], self.away_tactics,
            team_side="right", ball_xy=-ball_xy, is_team_in_possession=(b_own_prev == 1)
        )
        r_act_mapped = [ACTION_MIRROR_MAP.get(a, a) for a in r_act_tactical]
        comb_act = l_act + r_act_mapped

        # C++ physics step
        raw_next, _, done, _ = self.env.step(comb_act)
        self.raw_obs = raw_next
        self.done = done

        # Optional full state recording for 3D replay
        if self.archive_writer is not None:
            self.archive_writer.append(self.env.get_state())

        step = self.step_idx
        o0 = raw_next[0]

        # Record trajectory arrays
        if self.rec_players is not None:
            self.rec_players[step, :11] = o0['left_team']
            self.rec_players[step, 11:] = o0['right_team']
            self.rec_player_dirs[step, :11] = o0['left_team_direction']
            self.rec_player_dirs[step, 11:] = o0['right_team_direction']
            self.rec_balls[step] = o0['ball']
            self.rec_ball_dirs[step] = o0['ball_direction']
            self.rec_actions[step] = comb_act
            self.curr_score = [int(o0['score'][0]), int(o0['score'][1])]
            self.rec_scores[step] = np.array(self.curr_score, dtype=np.uint8)

            if 'game_mode' not in o0 or 'ball_owned_team' not in o0 or 'ball_owned_player' not in o0:
                raise ReplayIntegrityError("GRF observation missing required fields")

            self.rec_game_modes[step] = int(o0['game_mode'])
            self.rec_owned_teams[step] = int(o0['ball_owned_team'])
            self.rec_owned_players[step] = int(o0['ball_owned_player'])
        else:
            self.curr_score = [int(o0['score'][0]), int(o0['score'][1])]

        b_own = o0['ball_owned_team']
        b_player = o0['ball_owned_player']
        if b_own == 0:
            self.left_poss += 1
            if b_player >= 0:
                self.last_home_touch = b_player
        elif b_own == 1:
            self.right_poss += 1
            if b_player >= 0:
                self.last_away_touch = b_player

        sim_time_sec = step * SIM_STEP_SECONDS
        m_min = max(1, min(90, int(sim_time_sec / 60) + 1))

        # Pass State Machine
        if b_own == 0 and b_player >= 1 and (b_player - 1) < len(l_act):
            if l_act[b_player - 1] in (9, 10, 11):
                self.passes_h_att += 1
                self.active_pass = {"team": 0, "passer": b_player, "step": step}
        elif b_own == 1 and b_player >= 1 and (b_player - 1) < len(r_act_tactical):
            if r_act_tactical[b_player - 1] in (9, 10, 11):
                self.passes_a_att += 1
                self.active_pass = {"team": 1, "passer": b_player, "step": step}

        if self.active_pass is not None:
            ap = self.active_pass
            if b_own == ap["team"]:
                if b_player != ap["passer"] and b_player >= 0:
                    if ap["team"] == 0:
                        self.passes_h_cmp += 1
                    else:
                        self.passes_a_cmp += 1
                    self.active_pass = None
            elif b_own != -1 and b_own != ap["team"]:
                self.active_pass = None
            elif step - ap["step"] > 30:
                self.active_pass = None

        # Shot State Machine
        if b_own == 0 and b_player >= 1 and (b_player - 1) < len(l_act):
            if l_act[b_player - 1] == 12:
                self.shots_h += 1
                shot_x = float(o0['left_team'][b_player][0])
                shot_y = float(o0['left_team'][b_player][1])
                shooter_profile = self.home_tactics.roster[b_player] if b_player < len(self.home_tactics.roster) else self.home_tactics.roster[0]
                away_gk_profile = self.away_tactics.roster[0] if len(self.away_tactics.roster) > 0 else None
                away_gk_pos = (float(o0['right_team'][0][0]), float(o0['right_team'][0][1]))
                calc_xg = compute_shot_xg(
                    shooter_x=shot_x, shooter_y=shot_y, goal_x=1.0,
                    defenders=np.array(o0['right_team'], dtype=np.float32),
                    shooting_attr=getattr(shooter_profile, 'shooting', 70.0),
                    gk_pos=away_gk_pos,
                    gk_save_coverage=getattr(away_gk_profile, 'gk_save_coverage', 1.0)
                )
                self.xg_h += calc_xg
                shooter_name = self.home_players[b_player] if b_player < len(self.home_players) else f"Player {b_player}"
                self.events.append({
                    "minute": m_min, "step": step, "type": "shot", "team": "home",
                    "player": shooter_name, "xg": round(calc_xg, 3), "on_target": False
                })
                self.active_shot = {"team": 0, "shooter": shooter_name, "xg": calc_xg, "step": step}
        elif b_own == 1 and b_player >= 1 and (b_player - 1) < len(r_act_tactical):
            if r_act_tactical[b_player - 1] == 12:
                self.shots_a += 1
                shot_x = float(o0['right_team'][b_player][0])
                shot_y = float(o0['right_team'][b_player][1])
                shooter_profile = self.away_tactics.roster[b_player] if b_player < len(self.away_tactics.roster) else self.away_tactics.roster[0]
                home_gk_profile = self.home_tactics.roster[0] if len(self.home_tactics.roster) > 0 else None
                home_gk_pos = (float(o0['left_team'][0][0]), float(o0['left_team'][0][1]))
                calc_xg = compute_shot_xg(
                    shooter_x=shot_x, shooter_y=shot_y, goal_x=-1.0,
                    defenders=np.array(o0['left_team'], dtype=np.float32),
                    shooting_attr=getattr(shooter_profile, 'shooting', 70.0),
                    gk_pos=home_gk_pos,
                    gk_save_coverage=getattr(home_gk_profile, 'gk_save_coverage', 1.0)
                )
                self.xg_a += calc_xg
                shooter_name = self.away_players[b_player] if b_player < len(self.away_players) else f"Player {b_player}"
                self.events.append({
                    "minute": m_min, "step": step, "type": "shot", "team": "away",
                    "player": shooter_name, "xg": round(calc_xg, 3), "on_target": False
                })
                self.active_shot = {"team": 1, "shooter": shooter_name, "xg": calc_xg, "step": step}

        if self.active_shot is not None:
            if step - self.active_shot["step"] > 25:
                self.active_shot = None

        # Goal Detection
        if self.curr_score[0] > self.last_score[0]:
            scorer = "Home Player"
            if self.active_shot and self.active_shot["team"] == 0:
                scorer = self.active_shot["shooter"]
                self.sot_h += 1
            else:
                # Direct tap-in / unclassified finish: credit shot, SoT, and tap-in xG
                self.shots_h += 1
                self.sot_h += 1
                tap_in_xg = 0.65
                self.xg_h += tap_in_xg
                if self.last_home_touch < len(self.home_players):
                    scorer = self.home_players[self.last_home_touch]
                self.events.append({
                    "minute": m_min, "step": step, "type": "shot", "team": "home",
                    "player": scorer, "xg": tap_in_xg, "on_target": True
                })

            self.events.append({
                "minute": m_min, "step": step, "type": "goal", "team": "home",
                "scorer": scorer, "score": f"{self.curr_score[0]}-{self.curr_score[1]}"
            })
            self.last_score[0] = self.curr_score[0]
            self.active_shot = None

        if self.curr_score[1] > self.last_score[1]:
            scorer = "Away Player"
            if self.active_shot and self.active_shot["team"] == 1:
                scorer = self.active_shot["shooter"]
                self.sot_a += 1
            else:
                # Direct tap-in / unclassified finish: credit shot, SoT, and tap-in xG
                self.shots_a += 1
                self.sot_a += 1
                tap_in_xg = 0.65
                self.xg_a += tap_in_xg
                if self.last_away_touch < len(self.away_players):
                    scorer = self.away_players[self.last_away_touch]
                self.events.append({
                    "minute": m_min, "step": step, "type": "shot", "team": "away",
                    "player": scorer, "xg": tap_in_xg, "on_target": True
                })

            self.events.append({
                "minute": m_min, "step": step, "type": "goal", "team": "away",
                "scorer": scorer, "score": f"{self.curr_score[0]}-{self.curr_score[1]}"
            })
            self.last_score[1] = self.curr_score[1]
            self.active_shot = None

        # Half-Time Event
        if step == (self.max_steps // 2):
            self.events.append({
                "minute": 45, "step": step, "type": "half_time",
                "score": f"{self.curr_score[0]}-{self.curr_score[1]}"
            })

        self.step_idx += 1
        if self.done and self.actual_steps is None:
            self.actual_steps = self.step_idx

        # Next observations
        next_obs = self.get_initial_observations() if not self.done else np.zeros((20, 268), dtype=np.float32)
        return next_obs, self.done, {"curr_score": self.curr_score, "step": self.step_idx}

    def finalize(self) -> Dict[str, Any]:
        """Finalizes trajectory, closes archive and environment, and returns complete summary."""
        total_steps = self.actual_steps if self.actual_steps is not None else self.step_idx
        self.env.close()

        if self.archive_writer is not None:
            self.archive_writer.close()

        # Add full time event
        self.events.append({
            "minute": 90, "step": total_steps, "type": "full_time",
            "score": f"{self.curr_score[0]}-{self.curr_score[1]}"
        })

        tot_p = max(1, self.left_poss + self.right_poss)
        poss_h = round((self.left_poss / tot_p) * 100.0, 1)
        poss_a = round(100.0 - poss_h, 1)

        # Enforce strict domain statistical hierarchy: Shots >= SoT >= Score
        self.sot_h = max(self.sot_h, self.curr_score[0])
        self.shots_h = max(self.shots_h, self.sot_h)
        self.sot_a = max(self.sot_a, self.curr_score[1])
        self.shots_a = max(self.shots_a, self.sot_a)

        result_dict = {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.curr_score[0],
            "away_score": self.curr_score[1],
            "home_xg": round(self.xg_h, 2),
            "away_xg": round(self.xg_a, 2),
            "home_shots": self.shots_h,
            "away_shots": self.shots_a,
            "home_shots_on_target": self.sot_h,
            "away_shots_on_target": self.sot_a,
            "home_possession": poss_h,
            "away_possession": poss_a,
            "home_passes_completed": self.passes_h_cmp,
            "home_passes_attempted": self.passes_h_att,
            "away_passes_completed": self.passes_a_cmp,
            "away_passes_attempted": self.passes_a_att,
            "events": self.events,
            "total_steps": total_steps,
            "seed_val": self.seed_val,
        }

        # Save trajectory NPZ if requested
        if self.rec_players is not None and self.trace_npz:
            os.makedirs(os.path.dirname(self.trace_npz) or ".", exist_ok=True)
            manifest = MatchManifest(
                match_id=self.match_id,
                home_team=self.home_team,
                away_team=self.away_team,
                home_score=self.curr_score[0],
                away_score=self.curr_score[1],
                score=(self.curr_score[0], self.curr_score[1]),
                total_steps=total_steps,
                possession=(poss_h, poss_a),
                shots=(self.shots_h, self.shots_a),
                shots_on_target=(self.sot_h, self.sot_a),
                xg=(round(self.xg_h, 2), round(self.xg_a, 2)),
                passes_attempted=(self.passes_h_att, self.passes_a_att),
                passes_completed=(self.passes_h_cmp, self.passes_a_cmp),
                events=self.events,
                home_players=self.home_players,
                away_players=self.away_players,
                home_formation=self.home_formation,
                away_formation=self.away_formation,
                home_color=self.home_color,
                away_color=self.away_color,
                engine_fingerprint={
                    "engine": "GRF+TiKick-ProcessPool", "engine_version": "2.1.0",
                    "seed": self.seed_val, "determinism_level": 2,
                },
                video_url=f"/recordings/match_{self.match_id}.mp4",
                created_at=self.fixture.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
            traj = MatchTrajectory(
                match_id=self.match_id,
                seed=self.seed_val,
                total_steps=total_steps,
                player_coords=self.rec_players[:total_steps],
                player_dirs=self.rec_player_dirs[:total_steps],
                ball_coords=self.rec_balls[:total_steps],
                ball_dirs=self.rec_ball_dirs[:total_steps],
                actions=self.rec_actions[:total_steps],
                scores=self.rec_scores[:total_steps],
                manifest=manifest,
                game_mode=self.rec_game_modes[:total_steps],
                ball_owned_team=self.rec_owned_teams[:total_steps],
                ball_owned_player=self.rec_owned_players[:total_steps],
            )
            traj.save_to_npz(Path(self.trace_npz))
            result_dict["trace_npz"] = self.trace_npz

        return result_dict
