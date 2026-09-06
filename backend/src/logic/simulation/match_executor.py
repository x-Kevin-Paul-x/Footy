"""
Canonical GRFMatchExecutor & Simulation Specifications for Footy.
Single source of truth for match execution across single-match, batch, and WSL executors.
Encapsulates 11v11 GRF physics, tactical modulation, canonical feature extraction,
preallocated trajectory recording, and state archiving.
"""

import os
import sys
import time
import json
import enum
import hashlib
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np

try:
    import gym
except ImportError:
    try:
        import gymnasium as gym
    except ImportError:
        gym = None

try:
    import gfootball.env as football_env
except ImportError:
    football_env = None

from logic.grf_trajectory import MatchTrajectory, MatchManifest
from logic.grf_state_archive import GRFStateArchiveWriter, ReplayIntegrityError
from logic.replay_schema import SIM_STEP_SECONDS
from logic.grf_core import (
    extract_canonical_features,
    compute_shot_xg,
    apply_tactical_action_bias,
    ACTION_MIRROR_MAP,
)
from logic.footy_grf_adapter import (
    FootyGRFAdapter,
    FORMATION_COORDINATES,
    GRFPlayerProfile,
    GRFTeamTactics,
)


class ReplayMode(enum.Enum):
    NONE = "none"              # Fastest: only compute match result/stats, skip trajectory recording
    TRAJECTORY = "trajectory"  # Standard: record 2D player/ball coordinates & events for analytics
    FULL_STATE = "full_state"  # Broadcast: record full C++ engine state bytes to .grfstate archive


@dataclass
class SimulationSpec:
    """Canonical specification for a match simulation."""
    match_id: str = "match_0"
    home_team: str = "Home Team"
    away_team: str = "Away Team"
    fixture_id: Optional[str] = None
    season_year: Optional[int] = None
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    seed_val: Optional[int] = None
    max_steps: int = 1200
    replay_mode: ReplayMode = ReplayMode.FULL_STATE
    home_formation: str = "4-3-3"
    away_formation: str = "4-2-3-1"
    home_players: Optional[List[str]] = None
    away_players: Optional[List[str]] = None
    home_profiles: Optional[List[Any]] = None
    away_profiles: Optional[List[Any]] = None
    home_offensive_bias: float = 50.0
    home_defensive_bias: float = 50.0
    home_pressing_intensity: float = 50.0
    home_tempo: float = 50.0
    away_offensive_bias: float = 50.0
    away_defensive_bias: float = 50.0
    away_pressing_intensity: float = 50.0
    away_tempo: float = 50.0
    home_color: str = "#e63946"
    away_color: str = "#2196f3"
    trace_npz: Optional[str] = None
    states_file: Optional[str] = None
    trace_dump: Optional[str] = None
    record_dump: bool = False
    record_3d_video: bool = False
    render_mode: str = "3d"
    output_mp4: Optional[str] = None
    run_id: Optional[str] = None
    created_at: Optional[str] = None
    spec_version: str = "1.0.0"

    def __post_init__(self):
        if self.fixture_id and (not self.match_id or self.match_id == "match_0"):
            self.match_id = str(self.fixture_id)
        else:
            self.match_id = str(self.match_id)
        if self.home_team_name and self.home_team == "Home Team":
            self.home_team = str(self.home_team_name)
        if self.away_team_name and self.away_team == "Away Team":
            self.away_team = str(self.away_team_name)
        if self.seed_val is None:
            self.seed_val = int.from_bytes(
                hashlib.sha256(f"match_{self.match_id}".encode()).digest()[:4], "little"
            )
        else:
            self.seed_val = int(self.seed_val)

        if isinstance(self.replay_mode, str):
            self.replay_mode = ReplayMode(self.replay_mode)

    @classmethod
    def from_dict(cls, d: Dict[str, Any], max_steps: Optional[int] = None, replay_mode: Optional[Union[ReplayMode, str]] = None) -> "SimulationSpec":
        effective_max_steps = int(max_steps or d.get("max_steps", 1200))
        effective_replay_mode = replay_mode or d.get("replay_mode", ReplayMode.FULL_STATE)
        if isinstance(effective_replay_mode, str):
            effective_replay_mode = ReplayMode(effective_replay_mode)

        match_id = str(d.get("match_id", f"match_{int(time.time()*1000)%100000}"))
        trace_npz = d.get("trace_npz") or d.get("trajectory_file")
        states_file = d.get("states_file")
        trace_dump = d.get("trace_dump")
        render_mode = str(d.get("render_mode", os.getenv("FOOTY_DEFAULT_RENDER_MODE", "3d"))).lower()
        record_3d_video = bool(d.get("record_3d_video", False))

        return cls(
            match_id=match_id,
            home_team=str(d.get("home_team", "Home Team")),
            away_team=str(d.get("away_team", "Away Team")),
            seed_val=d.get("seed_val"),
            max_steps=effective_max_steps,
            replay_mode=effective_replay_mode,
            home_formation=str(d.get("home_formation", "4-3-3")),
            away_formation=str(d.get("away_formation", "4-2-3-1")),
            home_players=d.get("home_players"),
            away_players=d.get("away_players"),
            home_profiles=d.get("home_profiles"),
            away_profiles=d.get("away_profiles"),
            home_offensive_bias=float(d.get("home_offensive_bias", 50.0)),
            home_defensive_bias=float(d.get("home_defensive_bias", 50.0)),
            home_pressing_intensity=float(d.get("home_pressing_intensity", 50.0)),
            home_tempo=float(d.get("home_tempo", 50.0)),
            away_offensive_bias=float(d.get("away_offensive_bias", 50.0)),
            away_defensive_bias=float(d.get("away_defensive_bias", 50.0)),
            away_pressing_intensity=float(d.get("away_pressing_intensity", 50.0)),
            away_tempo=float(d.get("away_tempo", 50.0)),
            home_color=str(d.get("home_color", "#e63946")),
            away_color=str(d.get("away_color", "#2196f3")),
            trace_npz=trace_npz,
            states_file=states_file,
            trace_dump=trace_dump,
            record_dump=bool(d.get("record_dump", False) or record_3d_video or trace_dump),
            record_3d_video=record_3d_video,
            render_mode=render_mode,
            output_mp4=d.get("output_mp4"),
            run_id=d.get("run_id"),
            created_at=d.get("created_at"),
            spec_version="1.0.0",
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["replay_mode"] = self.replay_mode.value
        return d


@dataclass
class SimulationTransition:
    """State transition record for attribution and step analysis."""
    step: int
    match_minute: int
    pre_ball_xy: Tuple[float, float]
    pre_ball_owned_team: int
    pre_ball_owned_player: int
    post_ball_xy: Tuple[float, float]
    post_ball_owned_team: int
    post_ball_owned_player: int
    actions: List[int]
    game_mode: int
    curr_score: Tuple[int, int]
    events: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CanonicalMatchResult:
    """Typed canonical result object conforming to schema v2.1.0."""
    match_id: str
    home_team: str
    away_team: str
    score: Tuple[int, int]
    home_score: int
    away_score: int
    xg: Tuple[float, float]
    home_xg: float
    away_xg: float
    shots: Tuple[int, int]
    home_shots: int
    away_shots: int
    shots_on_target: Tuple[int, int]
    home_shots_on_target: int
    away_shots_on_target: int
    possession: Tuple[float, float]
    home_possession: float
    away_possession: float
    passes_completed: Tuple[int, int]
    home_passes_completed: int
    away_passes_completed: int
    passes_attempted: Tuple[int, int]
    home_passes_attempted: int
    away_passes_attempted: int
    events: List[Dict[str, Any]]
    simulation_steps: int
    total_steps: int
    seed_val: int
    trajectory_file: Optional[str] = None
    trace_file: Optional[str] = None
    trace_npz: Optional[str] = None
    trajectory_hash: Optional[str] = None
    states_file: Optional[str] = None
    dump_file: Optional[str] = None
    video_url: Optional[str] = None
    render_mode_used: Optional[str] = None
    match_duration_sec: Optional[float] = None
    result_schema_version: str = "2.1.0"

    @property
    def home_goals(self) -> int:
        return self.home_score

    @property
    def away_goals(self) -> int:
        return self.away_score

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["home_goals"] = self.home_score
        d["away_goals"] = self.away_score
        d["score"] = list(self.score)
        d["xg"] = list(self.xg)
        d["shots"] = list(self.shots)
        d["shots_on_target"] = list(self.shots_on_target)
        d["possession"] = list(self.possession)
        d["passes_completed"] = list(self.passes_completed)
        d["passes_attempted"] = list(self.passes_attempted)
        for k, v in self.__dict__.items():
            if k not in d:
                d[k] = v
        return d

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self.to_dict()

    def keys(self):
        return self.to_dict().keys()

    def values(self):
        return self.to_dict().values()

    def items(self):
        return self.to_dict().items()


class GRFMatchExecutor:
    """
    Consolidated Single-Match GRF Execution Engine.
    Shared across standalone runs, persistent daemons, dynamic worker pools, and batch executors.
    Encapsulates 11v11 GRF environment initialization, canonical state & tactical transforms,
    state machines (shots, xG, passes, goals), and artifact output.
    """

    def __init__(
        self,
        fixture_or_spec: Union[SimulationSpec, Dict[str, Any]],
        max_steps: Optional[int] = None,
        replay_mode: Optional[Union[ReplayMode, str]] = None
    ):
        if isinstance(fixture_or_spec, SimulationSpec):
            self.spec = fixture_or_spec
        else:
            self.spec = SimulationSpec.from_dict(fixture_or_spec, max_steps=max_steps, replay_mode=replay_mode)

        # Compatibility attributes
        self.fixture = self.spec.to_dict()
        self.max_steps = self.spec.max_steps
        self.replay_mode = self.spec.replay_mode
        self.match_id = self.spec.match_id
        self.seed_val = self.spec.seed_val

        # Deterministic PRNG seeding
        import random
        import torch
        seed_32 = self.seed_val % (2**31 - 1)
        np.random.seed(seed_32)
        random.seed(seed_32)
        torch.manual_seed(seed_32)

        # Team identity & tactics setup
        self.home_team = self.spec.home_team
        self.away_team = self.spec.away_team
        self.home_players = self.spec.home_players or [f"{self.home_team} Player {i+1}" for i in range(11)]
        self.away_players = self.spec.away_players or [f"{self.away_team} Player {i+1}" for i in range(11)]
        self.home_formation = self.spec.home_formation
        self.away_formation = self.spec.away_formation

        raw_h_profiles = self.spec.home_profiles
        if raw_h_profiles and isinstance(raw_h_profiles, list):
            h_roster = [GRFPlayerProfile(**p) if isinstance(p, dict) else p for p in raw_h_profiles]
        else:
            h_roster = [
                FootyGRFAdapter.extract_player_profile(p, assigned_pos="GK" if i == 0 else "CM")
                for i, p in enumerate(self.home_players[:11])
            ]
        while len(h_roster) < 11:
            h_roster.append(GRFPlayerProfile(name=f"{self.home_team} Player {len(h_roster)+1}"))

        raw_a_profiles = self.spec.away_profiles
        if raw_a_profiles and isinstance(raw_a_profiles, list):
            a_roster = [GRFPlayerProfile(**p) if isinstance(p, dict) else p for p in raw_a_profiles]
        else:
            a_roster = [
                FootyGRFAdapter.extract_player_profile(p, assigned_pos="GK" if i == 0 else "CM")
                for i, p in enumerate(self.away_players[:11])
            ]
        while len(a_roster) < 11:
            a_roster.append(GRFPlayerProfile(name=f"{self.away_team} Player {len(a_roster)+1}"))

        self.home_tactics = GRFTeamTactics(
            team_name=self.home_team,
            formation=self.home_formation if self.home_formation in FORMATION_COORDINATES else "4-3-3",
            offensive_bias=self.spec.home_offensive_bias,
            defensive_bias=self.spec.home_defensive_bias,
            pressing_intensity=self.spec.home_pressing_intensity,
            tempo=self.spec.home_tempo,
            roster=h_roster,
        )
        self.away_tactics = GRFTeamTactics(
            team_name=self.away_team,
            formation=self.away_formation if self.away_formation in FORMATION_COORDINATES else "4-2-3-1",
            offensive_bias=self.spec.away_offensive_bias,
            defensive_bias=self.spec.away_defensive_bias,
            pressing_intensity=self.spec.away_pressing_intensity,
            tempo=self.spec.away_tempo,
            roster=a_roster,
        )

        self.home_anchors = self.home_tactics.get_formation_anchors(is_right_team=False)[1:]
        self.away_anchors = self.away_tactics.get_formation_anchors(is_right_team=True)[1:]

        self.home_color = self.spec.home_color
        self.away_color = self.spec.away_color
        self.trace_npz = self.spec.trace_npz
        self.states_file = self.spec.states_file

        self.render_mode = self.spec.render_mode
        self.record_3d_video = self.spec.record_3d_video
        self.dump_path = self.spec.trace_dump
        self.record_dump = self.spec.record_dump
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
        self.env = None
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
        self.events: List[Dict[str, Any]] = []

        # C++ GRF Environment instantiation
        other_opts = {
            'action_set': 'full',
            'random_seed': self.seed_val % (2**31 - 1),
        }
        if self.record_dump:
            other_opts['tracesdir'] = self.match_dump_dir
            other_opts['dump_full_episodes'] = True

        if self.record_3d_video:
            other_opts['write_video'] = True
            other_opts['display_game_stats'] = False
            other_opts['render_resolution_x'] = 1280
            other_opts['render_resolution_y'] = 720

        if football_env is None:
            # When football_env is not available (e.g. host test without GRF C++ bindings),
            # mark env as None; steps will be handled or test will mock step
            self.env = None
            self.raw_obs = None
            return

        try:
            self.env = football_env.create_environment(
                env_name="11_vs_11_kaggle",
                stacked=False,
                representation='raw',
                rewards='scoring',
                write_goal_dumps=False,
                write_full_episode_dumps=self.record_dump,
                render=self.record_3d_video,
                write_video=self.record_3d_video,
                number_of_left_players_agent_controls=10,
                number_of_right_players_agent_controls=10,
                other_config_options=other_opts
            )
            self.raw_obs = self.env.reset()
        except Exception:
            try:
                self.close()
            finally:
                if self.record_dump:
                    shutil.rmtree(self.match_dump_dir, ignore_errors=True)
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self) -> None:
        """Release native resources safely and idempotently."""
        errors = []
        archive_writer, self.archive_writer = self.archive_writer, None
        if archive_writer is not None:
            try:
                archive_writer.close()
            except Exception as exc:
                errors.append(f"state archive close failed: {exc}")

        env, self.env = self.env, None
        if env is not None:
            try:
                env.close()
            except Exception as exc:
                errors.append(f"GRF environment close failed: {exc}")

        if errors:
            raise RuntimeError("; ".join(errors))

    def abort(self, reason: str = "") -> None:
        """Immediately abort match execution and clean staging directory."""
        try:
            self.close()
        finally:
            if getattr(self, "match_dump_dir", None) and os.path.exists(self.match_dump_dir):
                shutil.rmtree(self.match_dump_dir, ignore_errors=True)

    def get_initial_observations(self) -> np.ndarray:
        """Extracts canonical 268-dim features for the 20 outfield agents (10 home, 10 away)."""
        if self.raw_obs is None:
            return np.zeros((20, 268), dtype=np.float32)

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

        if self.env is None:
            self.done = True
            return np.zeros((20, 268), dtype=np.float32), True, {"step": self.step_idx, "curr_score": self.curr_score}

        l_act_raw = raw_actions[0:10].tolist()
        r_act_raw = raw_actions[10:20].tolist()

        o_prev = self.raw_obs[0]
        ball_xy = np.array(o_prev['ball'][:2], dtype=np.float32)
        b_own_prev = o_prev.get('ball_owned_team', -1)
        b_player_prev = o_prev.get('ball_owned_player', -1)
        l_pos = np.array(o_prev['left_team'][1:], dtype=np.float32)
        r_pos = np.array(o_prev['right_team'][1:], dtype=np.float32)

        if b_own_prev == 0 and b_player_prev >= 0:
            self.last_home_touch = b_player_prev
        elif b_own_prev == 1 and b_player_prev >= 0:
            self.last_away_touch = b_player_prev

        # Tactical modulation
        l_act = apply_tactical_action_bias(
            l_act_raw, l_pos, self.home_anchors, self.home_tactics,
            team_side="left", ball_xy=ball_xy, is_team_in_possession=(b_own_prev == 0)
        )
        r_act_tactical = apply_tactical_action_bias(
            r_act_raw, -r_pos, [(-x, -y) for (x, y) in self.away_anchors], self.away_tactics,
            team_side="left", ball_xy=-ball_xy, is_team_in_possession=(b_own_prev == 1)
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

        total_match_steps = self.max_steps if getattr(self, "max_steps", None) else 1200
        m_min = max(1, min(90, int((step / max(1, total_match_steps)) * 90) + 1))

        # Pass State Machine
        if self.active_pass is None and b_own_prev == 0 and b_player_prev >= 1 and (b_player_prev - 1) < len(l_act):
            if l_act[b_player_prev - 1] in (9, 10, 11):
                self.passes_h_att += 1
                self.active_pass = {"team": 0, "passer": b_player_prev, "step": step}
        elif self.active_pass is None and b_own_prev == 1 and b_player_prev >= 1 and (b_player_prev - 1) < len(r_act_tactical):
            if r_act_tactical[b_player_prev - 1] in (9, 10, 11):
                self.passes_a_att += 1
                self.active_pass = {"team": 1, "passer": b_player_prev, "step": step}

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
        if self.active_shot is None and b_own_prev == 0 and b_player_prev >= 1 and (b_player_prev - 1) < len(l_act):
            if l_act[b_player_prev - 1] == 12:
                self.shots_h += 1
                shot_x = float(o_prev['left_team'][b_player_prev][0])
                shot_y = float(o_prev['left_team'][b_player_prev][1])
                shooter_profile = self.home_tactics.roster[b_player_prev] if b_player_prev < len(self.home_tactics.roster) else self.home_tactics.roster[0]
                away_gk_profile = self.away_tactics.roster[0] if len(self.away_tactics.roster) > 0 else None
                away_gk_pos = (float(o_prev['right_team'][0][0]), float(o_prev['right_team'][0][1]))
                calc_xg = compute_shot_xg(
                    shooter_x=shot_x, shooter_y=shot_y, goal_x=1.0,
                    defenders=np.array(o_prev['right_team'], dtype=np.float32),
                    shooting_attr=getattr(shooter_profile, 'shooting', 70.0),
                    gk_pos=away_gk_pos,
                    gk_save_coverage=getattr(away_gk_profile, 'gk_save_coverage', 1.0)
                )
                self.xg_h += calc_xg
                shooter_name = self.home_players[b_player_prev] if b_player_prev < len(self.home_players) else f"Player {b_player_prev}"
                self.events.append({
                    "minute": m_min, "step": step, "type": "shot", "team": "home",
                    "player": shooter_name, "xg": round(calc_xg, 3), "on_target": False,
                    "outcome": "PENDING"
                })
                self.active_shot = {"team": 0, "shooter": shooter_name, "xg": calc_xg, "step": step}
        elif self.active_shot is None and b_own_prev == 1 and b_player_prev >= 1 and (b_player_prev - 1) < len(r_act_tactical):
            if r_act_tactical[b_player_prev - 1] == 12:
                self.shots_a += 1
                shot_x = float(o_prev['right_team'][b_player_prev][0])
                shot_y = float(o_prev['right_team'][b_player_prev][1])
                shooter_profile = self.away_tactics.roster[b_player_prev] if b_player_prev < len(self.away_tactics.roster) else self.away_tactics.roster[0]
                home_gk_profile = self.home_tactics.roster[0] if len(self.home_tactics.roster) > 0 else None
                home_gk_pos = (float(o_prev['left_team'][0][0]), float(o_prev['left_team'][0][1]))
                calc_xg = compute_shot_xg(
                    shooter_x=shot_x, shooter_y=shot_y, goal_x=-1.0,
                    defenders=np.array(o_prev['left_team'], dtype=np.float32),
                    shooting_attr=getattr(shooter_profile, 'shooting', 70.0),
                    gk_pos=home_gk_pos,
                    gk_save_coverage=getattr(home_gk_profile, 'gk_save_coverage', 1.0)
                )
                self.xg_a += calc_xg
                shooter_name = self.away_players[b_player_prev] if b_player_prev < len(self.away_players) else f"Player {b_player_prev}"
                self.events.append({
                    "minute": m_min, "step": step, "type": "shot", "team": "away",
                    "player": shooter_name, "xg": round(calc_xg, 3), "on_target": False,
                    "outcome": "PENDING"
                })
                self.active_shot = {"team": 1, "shooter": shooter_name, "xg": calc_xg, "step": step}

        # Physical Shot Outcome Classifier
        if self.active_shot is not None:
            shot_team = self.active_shot["team"]
            opp_team = 1 - shot_team
            ball_x = float(o0['ball'][0])
            ball_y = float(o0['ball'][1])

            # 1. Check GK Save
            if b_own == opp_team and b_player == 0:
                if (shot_team == 0 and ball_x > 0.65) or (shot_team == 1 and ball_x < -0.65):
                    gk_name = self.away_players[0] if (shot_team == 0 and len(self.away_players) > 0) else (self.home_players[0] if len(self.home_players) > 0 else "Goalkeeper")
                    for ev in reversed(self.events):
                        if ev.get("type") == "shot" and ev.get("step") == self.active_shot["step"]:
                            ev["on_target"] = True
                            ev["outcome"] = "SAVED"
                            break

                    self.events.append({
                        "minute": m_min, "step": step, "type": "save",
                        "team": "away" if shot_team == 0 else "home", "player": gk_name
                    })
                    self.active_shot = None

            # 2. Check Hit Post / Crossbar
            elif ((shot_team == 0 and 0.98 <= ball_x <= 1.02) or (shot_team == 1 and -1.02 <= ball_x <= -0.98)) and (0.038 <= abs(ball_y) <= 0.055):
                for ev in reversed(self.events):
                    if ev.get("type") == "shot" and ev.get("step") == self.active_shot["step"]:
                        ev["on_target"] = False
                        ev["outcome"] = "HIT_POST"
                        break
                self.events.append({
                    "minute": m_min, "step": step, "type": "hit_post",
                    "team": "home" if shot_team == 0 else "away", "player": self.active_shot["shooter"]
                })
                self.active_shot = None

            # 3. Check Outfield Defender Block
            elif b_own == opp_team and b_player > 0:
                for ev in reversed(self.events):
                    if ev.get("type") == "shot" and ev.get("step") == self.active_shot["step"]:
                        ev["on_target"] = False
                        ev["outcome"] = "BLOCKED"
                        break
                self.active_shot = None

            # 4. Check Off-Target Endline Crossing
            elif (shot_team == 0 and ball_x >= 1.0 and abs(ball_y) > 0.08) or \
                 (shot_team == 1 and ball_x <= -1.0 and abs(ball_y) > 0.08):
                for ev in reversed(self.events):
                    if ev.get("type") == "shot" and ev.get("step") == self.active_shot["step"]:
                        ev["on_target"] = False
                        ev["outcome"] = "OFF_TARGET"
                        break
                self.active_shot = None

            # 5. Timeout: 25 steps elapsed without resolution
            elif step - self.active_shot["step"] > 25:
                for ev in reversed(self.events):
                    if ev.get("type") == "shot" and ev.get("step") == self.active_shot["step"] and ev.get("outcome") == "PENDING":
                        ev["outcome"] = "UNRESOLVED"
                        break
                self.active_shot = None

        # Goal Detection
        if self.curr_score[0] > self.last_score[0]:
            scorer = "Home Player"
            if self.active_shot and self.active_shot["team"] == 0:
                scorer = self.active_shot["shooter"]
                for ev in reversed(self.events):
                    if ev.get("type") == "shot" and ev.get("team") == "home" and ev.get("step") == self.active_shot["step"]:
                        ev["on_target"] = True
                        ev["outcome"] = "GOAL"
                        break
            else:
                striker_idx = self.last_home_touch if (0 <= self.last_home_touch < len(self.home_players)) else 9
                strike_x = float(o_prev['left_team'][striker_idx][0])
                strike_y = float(o_prev['left_team'][striker_idx][1])
                shooter_profile = self.home_tactics.roster[striker_idx] if striker_idx < len(self.home_tactics.roster) else self.home_tactics.roster[0]
                away_gk_profile = self.away_tactics.roster[0] if len(self.away_tactics.roster) > 0 else None
                away_gk_pos = (float(o_prev['right_team'][0][0]), float(o_prev['right_team'][0][1]))

                strike_xg = compute_shot_xg(
                    shooter_x=strike_x, shooter_y=strike_y, goal_x=1.0,
                    defenders=np.array(o_prev['right_team'], dtype=np.float32),
                    shooting_attr=getattr(shooter_profile, 'shooting', 70.0),
                    gk_pos=away_gk_pos,
                    gk_save_coverage=getattr(away_gk_profile, 'gk_save_coverage', 1.0)
                )
                scorer = self.home_players[striker_idx] if striker_idx < len(self.home_players) else f"Player {striker_idx}"
                self.events.append({
                    "minute": m_min, "step": step, "type": "shot", "team": "home",
                    "player": scorer, "xg": round(strike_xg, 3), "on_target": True,
                    "outcome": "GOAL"
                })

            self.events.append({
                "minute": m_min, "step": step, "type": "goal", "team": "home",
                "player": scorer, "scorer": scorer, "score": f"{self.curr_score[0]}-{self.curr_score[1]}",
                "causality": {
                    "ball_coord": [float(o0['ball'][0]), float(o0['ball'][1]), float(o0['ball'][2])],
                    "goal_mouth_y": float(o0['ball'][1]),
                    "score_transition": [self.last_score[0], self.curr_score[0]]
                }
            })
            self.last_score[0] = self.curr_score[0]
            self.active_shot = None

        if self.curr_score[1] > self.last_score[1]:
            scorer = "Away Player"
            if self.active_shot and self.active_shot["team"] == 1:
                scorer = self.active_shot["shooter"]
                for ev in reversed(self.events):
                    if ev.get("type") == "shot" and ev.get("team") == "away" and ev.get("step") == self.active_shot["step"]:
                        ev["on_target"] = True
                        ev["outcome"] = "GOAL"
                        break
            else:
                striker_idx = self.last_away_touch if (0 <= self.last_away_touch < len(self.away_players)) else 9
                strike_x = float(o_prev['right_team'][striker_idx][0])
                strike_y = float(o_prev['right_team'][striker_idx][1])
                shooter_profile = self.away_tactics.roster[striker_idx] if striker_idx < len(self.away_tactics.roster) else self.away_tactics.roster[0]
                home_gk_profile = self.home_tactics.roster[0] if len(self.home_tactics.roster) > 0 else None
                home_gk_pos = (float(o_prev['left_team'][0][0]), float(o_prev['left_team'][0][1]))

                strike_xg = compute_shot_xg(
                    shooter_x=strike_x, shooter_y=strike_y, goal_x=-1.0,
                    defenders=np.array(o_prev['left_team'], dtype=np.float32),
                    shooting_attr=getattr(shooter_profile, 'shooting', 70.0),
                    gk_pos=home_gk_pos,
                    gk_save_coverage=getattr(home_gk_profile, 'gk_save_coverage', 1.0)
                )
                scorer = self.away_players[striker_idx] if striker_idx < len(self.away_players) else f"Player {striker_idx}"
                self.events.append({
                    "minute": m_min, "step": step, "type": "shot", "team": "away",
                    "player": scorer, "xg": round(strike_xg, 3), "on_target": True,
                    "outcome": "GOAL"
                })

            self.events.append({
                "minute": m_min, "step": step, "type": "goal", "team": "away",
                "player": scorer, "scorer": scorer, "score": f"{self.curr_score[0]}-{self.curr_score[1]}",
                "causality": {
                    "ball_coord": [float(o0['ball'][0]), float(o0['ball'][1]), float(o0['ball'][2])],
                    "goal_mouth_y": float(o0['ball'][1]),
                    "score_transition": [self.last_score[1], self.curr_score[1]]
                }
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

        next_obs = self.get_initial_observations() if not self.done else np.zeros((20, 268), dtype=np.float32)
        return next_obs, self.done, {"curr_score": self.curr_score, "step": self.step_idx}

    def finalize(self) -> CanonicalMatchResult:
        """Finalizes trajectory, closes archive and environment, and returns CanonicalMatchResult."""
        total_steps = self.actual_steps if self.actual_steps is not None else self.step_idx
        self.close()

        # Add full time event
        self.events.append({
            "minute": 90, "step": max(0, total_steps - 1), "type": "full_time",
            "score": f"{self.curr_score[0]}-{self.curr_score[1]}"
        })

        tot_p = max(1, self.left_poss + self.right_poss)
        poss_h = round((self.left_poss / tot_p) * 100.0, 1)
        poss_a = round(100.0 - poss_h, 1)

        # Canonical Event Ledger Reducer
        shot_events_h = [e for e in self.events if e.get("type") == "shot" and e.get("team") == "home"]
        shot_events_a = [e for e in self.events if e.get("type") == "shot" and e.get("team") == "away"]

        shots_h_derived = len(shot_events_h)
        shots_a_derived = len(shot_events_a)
        sot_h_derived = len([e for e in shot_events_h if e.get("on_target", False)])
        sot_a_derived = len([e for e in shot_events_a if e.get("on_target", False)])
        xg_h_derived = round(float(sum(e.get("xg", 0.0) for e in shot_events_h)), 2)
        xg_a_derived = round(float(sum(e.get("xg", 0.0) for e in shot_events_a)), 2)

        manifest = MatchManifest(
            match_id=self.match_id,
            home_team=self.home_team,
            away_team=self.away_team,
            home_score=self.curr_score[0],
            away_score=self.curr_score[1],
            score=(self.curr_score[0], self.curr_score[1]),
            total_steps=total_steps,
            possession=(poss_h, poss_a),
            shots=(shots_h_derived, shots_a_derived),
            shots_on_target=(sot_h_derived, sot_a_derived),
            xg=(float(xg_h_derived), float(xg_a_derived)),
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
                "engine": "GRFMatchExecutor", "engine_version": "2.1.0",
                "seed": self.seed_val, "determinism_level": 2,
            },
            video_url=None,
            created_at=self.spec.created_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        trajectory_hash = None
        # Save trajectory NPZ if requested
        if self.rec_players is not None and self.trace_npz:
            os.makedirs(os.path.dirname(self.trace_npz) or ".", exist_ok=True)
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
            trajectory_hash = traj.compute_trajectory_hash()

        # Persist native .dump if available
        dump_out = None
        import glob
        if self.record_dump and self.dump_path and os.path.exists(self.match_dump_dir):
            dump_files = sorted(glob.glob(f"{self.match_dump_dir}/episode_done_*.dump"))
            if dump_files:
                os.makedirs(os.path.dirname(self.dump_path) or ".", exist_ok=True)
                shutil.move(dump_files[-1], self.dump_path)
                dump_out = self.dump_path

        # Handle 3D video if explicitly recorded during live sim
        video_url = None
        render_mode_used = None
        if self.record_3d_video and os.path.exists(self.match_dump_dir):
            avi_files = sorted(glob.glob(f"{self.match_dump_dir}/episode_done_*.avi"))
            if avi_files:
                raw_avi = avi_files[-1]
                custom_mp4 = self.spec.output_mp4
                run_id = self.spec.run_id
                if custom_mp4:
                    target_mp4 = custom_mp4
                else:
                    base_rec = "/mnt/c/Users/kevin/OneDrive/Desktop/Projects/Footy/backend/reports/recordings"
                    try:
                        import config
                        base_rec = str(config.RECORDINGS_DIR).replace("\\", "/")
                        if ":" in base_rec:
                            drive = base_rec[0].lower()
                            base_rec = f"/mnt/{drive}{base_rec[2:]}"
                    except Exception:
                        pass
                    target_mp4 = f"{base_rec}/{run_id}/match_{self.match_id}_3d.mp4" if run_id else f"{base_rec}/match_{self.match_id}_3d.mp4"

                os.makedirs(os.path.dirname(target_mp4) or '.', exist_ok=True)
                try:
                    from logic.grf_renderer import transcode_live_avi_to_broadcast_mp4
                    video_url = transcode_live_avi_to_broadcast_mp4(
                        raw_avi_path=raw_avi,
                        output_mp4_path=target_mp4,
                        manifest=manifest,
                        home_color=self.home_color,
                        away_color=self.away_color
                    )
                    render_mode_used = "3d"
                except Exception as e:
                    failed_source = f"{target_mp4}.source.avi"
                    try:
                        shutil.move(raw_avi, failed_source)
                    except OSError:
                        failed_source = raw_avi
                    if os.path.exists(self.match_dump_dir):
                        shutil.rmtree(self.match_dump_dir, ignore_errors=True)
                    raise RuntimeError(
                        f"3D video encoding failed; source preserved at {failed_source}: {e}"
                    ) from e

        if os.path.exists(self.match_dump_dir):
            shutil.rmtree(self.match_dump_dir, ignore_errors=True)

        return CanonicalMatchResult(
            match_id=self.match_id,
            home_team=self.home_team,
            away_team=self.away_team,
            score=(self.curr_score[0], self.curr_score[1]),
            home_score=self.curr_score[0],
            away_score=self.curr_score[1],
            xg=(xg_h_derived, xg_a_derived),
            home_xg=xg_h_derived,
            away_xg=xg_a_derived,
            shots=(shots_h_derived, shots_a_derived),
            home_shots=shots_h_derived,
            away_shots=shots_a_derived,
            shots_on_target=(sot_h_derived, sot_a_derived),
            home_shots_on_target=sot_h_derived,
            away_shots_on_target=sot_a_derived,
            possession=(poss_h, poss_a),
            home_possession=poss_h,
            away_possession=poss_a,
            passes_completed=(self.passes_h_cmp, self.passes_a_cmp),
            home_passes_completed=self.passes_h_cmp,
            away_passes_completed=self.passes_a_cmp,
            passes_attempted=(self.passes_h_att, self.passes_a_att),
            home_passes_attempted=self.passes_h_att,
            away_passes_attempted=self.passes_a_att,
            events=self.events,
            simulation_steps=total_steps,
            total_steps=total_steps,
            seed_val=self.seed_val,
            trajectory_file=self.trace_npz,
            trace_file=self.trace_npz,
            trace_npz=self.trace_npz,
            trajectory_hash=trajectory_hash,
            states_file=self.states_file,
            dump_file=dump_out,
            video_url=video_url,
            render_mode_used=render_mode_used,
            result_schema_version="2.1.0",
        )

    def execute(self, policy: Any = None) -> CanonicalMatchResult:
        """
        Execute the full match simulation through completion.
        Uses BatchedDQNPolicy by default or fallback heuristic if neural policy not specified.
        """
        if policy is None:
            try:
                from logic.simulation.simulation_process_pool import BatchedDQNPolicy
                policy = BatchedDQNPolicy(device="cpu", max_batch_size=1)
            except Exception:
                policy = None

        if policy is not None:
            policy.reset_match(self.match_id, self.seed_val)

        obs = self.get_initial_observations()
        done = False
        while not done and self.step_idx < self.max_steps:
            if policy is not None:
                acts = policy.evaluate(obs, match_ids=[self.match_id])
            else:
                acts = np.zeros(20, dtype=np.int32)
            obs, done, _ = self.step(acts)

        return self.finalize()
