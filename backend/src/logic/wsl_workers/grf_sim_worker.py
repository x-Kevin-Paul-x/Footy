"""
WSL Dedicated Worker: Pure GRF + TiKick MARL Match Simulation.
Executes 11v11 MARL physics at maximum throughput without rendering graphics or encoding video.
Outputs compact .npz trajectory, raw .dump trace, and verified MatchManifest JSON.
Supports both one-shot CLI execution and persistent daemon mode.
"""

import os
import sys
import json
import time
import hashlib
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import torch

# Ensure backend/src and third-party modules can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_src = os.path.dirname(os.path.dirname(script_dir))
if backend_src not in sys.path:
    sys.path.insert(0, backend_src)

import gym
import gfootball.env as football_env

from logic.grf_trajectory import MatchTrajectory, MatchManifest
from logic.grf_state_archive import GRFStateArchiveWriter, ReplayIntegrityError
from logic.grf_core import extract_canonical_features, compute_shot_xg, apply_tactical_action_bias, ACTION_MIRROR_MAP
from logic.footy_grf_adapter import FootyGRFAdapter, FORMATION_COORDINATES, GRFPlayerProfile, GRFTeamTactics


class TiKickModelConfig:
    hidden_size = 256
    gain = 0.01
    use_orthogonal = False
    activation_id = 1
    use_policy_active_masks = False
    use_naive_recurrent_policy = False
    use_recurrent_policy = True
    use_influence_policy = False
    influence_layer_N = 1
    use_policy_vhead = False
    recurrent_N = 1
    use_feature_normalization = True
    use_conv1d = False
    stacked_frames = 1
    layer_N = 3


_GLOBAL_POLICY = None
_GLOBAL_POLICY_PATH = None


def get_or_load_policy(ckpt_path: str, tikick_dir: str, device: torch.device):
    global _GLOBAL_POLICY, _GLOBAL_POLICY_PATH
    if _GLOBAL_POLICY is not None and _GLOBAL_POLICY_PATH == ckpt_path:
        return _GLOBAL_POLICY

    if tikick_dir and tikick_dir not in sys.path:
        sys.path.insert(0, tikick_dir)
    from tmarl.networks.policy_network import PolicyNetwork
    obs_space = gym.spaces.Box(low=-1e6, high=1e6, shape=(268,), dtype='float32')
    action_space = gym.spaces.Discrete(33)
    policy = PolicyNetwork(TiKickModelConfig(), obs_space, action_space, device=device)
    state_dict = torch.load(ckpt_path, map_location=device)
    policy.load_state_dict(state_dict)
    policy.eval()

    _GLOBAL_POLICY = policy
    _GLOBAL_POLICY_PATH = ckpt_path
    return policy


def run_simulation(payload: Dict[str, Any]) -> Dict[str, Any]:
    match_id = str(payload["match_id"])
    home_team = payload.get("home_team", "Home Team")
    away_team = payload.get("away_team", "Away Team")
    home_formation = payload.get("home_formation", "4-3-3")
    away_formation = payload.get("away_formation", "4-2-3-1")
    home_players = payload.get("home_players") or [f"{home_team} Player {i+1}" for i in range(11)]
    away_players = payload.get("away_players") or [f"{away_team} Player {i+1}" for i in range(11)]
    home_color = payload.get("home_color", "#e63946")
    away_color = payload.get("away_color", "#2196f3")
    max_steps = int(payload.get("max_steps", 1200))
    ckpt_path = payload["ckpt_path"]
    tikick_dir = payload.get("tikick_dir", "")
    trace_npz_path = payload.get("trace_npz")
    trace_dump_path = payload.get("trace_dump")
    seed_val = payload.get("seed_val")
    record_grf_states = bool(payload.get("record_grf_states", False))
    record_dump = bool(payload.get("record_dump", False))
    states_file_path = payload.get("states_file")

    # Full 32-bit Seed Space
    if seed_val is None:
        seed_val = int.from_bytes(hashlib.sha256(f"match_{match_id}".encode()).digest()[:4], "little")
    else:
        seed_val = int(seed_val)

    # Deterministic Seeding Protocol across all PRNGs
    random.seed(seed_val)
    np.random.seed(seed_val)
    torch.manual_seed(seed_val)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed_val)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    policy = get_or_load_policy(ckpt_path, tikick_dir, device)

    # Build Team Simulation Contexts & Rosters
    raw_h_profiles = payload.get("home_profiles")
    if raw_h_profiles and isinstance(raw_h_profiles, list):
        home_roster = [GRFPlayerProfile(**p) if isinstance(p, dict) else p for p in raw_h_profiles]
    else:
        home_roster = [FootyGRFAdapter.extract_player_profile(p, assigned_pos="GK" if i == 0 else "CM")
                       for i, p in enumerate(home_players[:11])]
    while len(home_roster) < 11:
        home_roster.append(GRFPlayerProfile(name=f"{home_team} Player {len(home_roster)+1}"))

    raw_a_profiles = payload.get("away_profiles")
    if raw_a_profiles and isinstance(raw_a_profiles, list):
        away_roster = [GRFPlayerProfile(**p) if isinstance(p, dict) else p for p in raw_a_profiles]
    else:
        away_roster = [FootyGRFAdapter.extract_player_profile(p, assigned_pos="GK" if i == 0 else "CM")
                       for i, p in enumerate(away_players[:11])]
    while len(away_roster) < 11:
        away_roster.append(GRFPlayerProfile(name=f"{away_team} Player {len(away_roster)+1}"))

    home_tactics = GRFTeamTactics(
        team_name=home_team,
        formation=home_formation if home_formation in FORMATION_COORDINATES else "4-3-3",
        offensive_bias=float(payload.get("home_offensive_bias", 50.0)),
        defensive_bias=float(payload.get("home_defensive_bias", 50.0)),
        pressing_intensity=float(payload.get("home_pressing_intensity", 50.0)),
        tempo=float(payload.get("home_tempo", 50.0)),
        roster=home_roster
    )
    away_tactics = GRFTeamTactics(
        team_name=away_team,
        formation=away_formation if away_formation in FORMATION_COORDINATES else "4-2-3-1",
        offensive_bias=float(payload.get("away_offensive_bias", 50.0)),
        defensive_bias=float(payload.get("away_defensive_bias", 50.0)),
        pressing_intensity=float(payload.get("away_pressing_intensity", 50.0)),
        tempo=float(payload.get("away_tempo", 50.0)),
        roster=away_roster
    )

    # 10 field player anchors (excluding GK at idx 0)
    home_anchors = home_tactics.get_formation_anchors(is_right_team=False)[1:]
    away_anchors = away_tactics.get_formation_anchors(is_right_team=True)[1:]

    # Dumps directory for native GRF trace recording (only if debug/record_dump requested)
    match_dump_dir = f"/tmp/dumps/tmp_{match_id}_{int(time.time()*1000)%100000}"
    if record_dump:
        os.makedirs(match_dump_dir, exist_ok=True)

    other_opts = {
        'action_set': 'full',
        'random_seed': seed_val % (2**31 - 1),
    }
    if record_dump:
        other_opts['tracesdir'] = match_dump_dir
        other_opts['dump_full_episodes'] = True

    env = football_env.create_environment(
        env_name="11_vs_11_kaggle",
        stacked=False,
        representation='raw',
        rewards='scoring',
        write_goal_dumps=False,
        write_full_episode_dumps=record_dump,
        render=False,
        number_of_left_players_agent_controls=10,
        number_of_right_players_agent_controls=10,
        other_config_options=other_opts
    )

    raw_obs = env.reset()
    num_agents = 10

    # Pre-allocated tensors & state buffers
    left_rnn_states = torch.zeros((num_agents, 1, 256), dtype=torch.float32, device=device)
    left_masks = torch.ones((num_agents, 1), dtype=torch.float32, device=device)
    left_avail = torch.zeros((num_agents, 33), dtype=torch.float32, device=device)
    left_avail[:, :20] = 1.0
    left_loff = np.zeros(11, dtype=np.float32)
    left_roff = np.zeros(11, dtype=np.float32)

    right_rnn_states = torch.zeros((num_agents, 1, 256), dtype=torch.float32, device=device)
    right_masks = torch.ones((num_agents, 1), dtype=torch.float32, device=device)
    right_avail = torch.zeros((num_agents, 33), dtype=torch.float32, device=device)
    right_avail[:, :20] = 1.0
    right_loff = np.zeros(11, dtype=np.float32)
    right_roff = np.zeros(11, dtype=np.float32)

    # Trajectory recording buffers
    recorded_players = np.empty((max_steps, 22, 2), dtype=np.float32)
    recorded_player_dirs = np.empty((max_steps, 22, 2), dtype=np.float32)
    recorded_balls = np.empty((max_steps, 3), dtype=np.float32)
    recorded_ball_dirs = np.empty((max_steps, 3), dtype=np.float32)
    recorded_actions = np.empty((max_steps, 20), dtype=np.uint8)
    recorded_scores = np.empty((max_steps, 2), dtype=np.uint8)
    recorded_game_modes = np.empty(max_steps, dtype=np.int8)
    recorded_owned_teams = np.empty(max_steps, dtype=np.int8)
    recorded_owned_players = np.empty(max_steps, dtype=np.int8)

    # Streaming chunked GRF state writer (zero overhead if record_grf_states=False)
    state_writer = None
    if record_grf_states:
        resolved_states_path = states_file_path or (
            str(trace_npz_path).replace('.npz', '.grfstate') if trace_npz_path
            else f"/tmp/states_{match_id}.grfstate"
        )
        state_writer = GRFStateArchiveWriter(resolved_states_path, match_id=match_id, chunk_size=50)

    # Match state & statistics
    curr_score = [0, 0]
    last_score = [0, 0]
    left_poss = 0
    right_poss = 0
    shots_h = 0
    shots_a = 0
    sot_h = 0
    sot_a = 0
    xg_h = 0.0
    xg_a = 0.0
    passes_h_att = 0
    passes_h_cmp = 0
    passes_a_att = 0
    passes_a_cmp = 0

    # Rigorous Event State Machine Trackers
    active_pass: Optional[Dict[str, Any]] = None
    active_shot: Optional[Dict[str, Any]] = None
    last_home_touch = 10
    last_away_touch = 10
    events = []
    half_time_recorded = False
    half_time_step = max_steps // 2

    step = 0
    done = False

    try:
        while not done and step < max_steps:
            # Check for Half-Time transition
            if step == half_time_step and not half_time_recorded:
                half_time_recorded = True
                events.append({
                    "step": step,
                    "sim_time": round(step * 0.1, 2),
                    "minute": 45,
                    "type": "half_time",
                    "score": f"{curr_score[0]}-{curr_score[1]}",
                    "details": f"Half Time • {home_team} {curr_score[0]} - {curr_score[1]} {away_team}"
                })

            # 1. Canonical perspective feature extraction
            obs_l, left_loff, left_roff = extract_canonical_features(
                raw_obs[0:num_agents], team_side="left", num_agents=num_agents,
                last_loff=left_loff, last_roff=left_roff
            )
            obs_r, right_loff, right_roff = extract_canonical_features(
                raw_obs[num_agents:num_agents*2], team_side="right", num_agents=num_agents,
                last_loff=right_loff, last_roff=right_roff
            )

            obs_batch_np = np.concatenate([obs_l, obs_r], axis=0)
            obs_batch_t = torch.from_numpy(obs_batch_np).to(device)

            rnn_batch = torch.cat([left_rnn_states, right_rnn_states], dim=0)
            masks_batch = torch.cat([left_masks, right_masks], dim=0)
            avail_batch = torch.cat([left_avail, right_avail], dim=0)

            # 2. TiKick Neural Policy Inference
            with torch.inference_mode():
                actions_batch, _, next_rnn_batch = policy(
                    obs_batch_t, rnn_batch, masks_batch, avail_batch, deterministic=True
                )

            left_rnn_states = next_rnn_batch[:num_agents]
            right_rnn_states = next_rnn_batch[num_agents:]

            actions_np = actions_batch.cpu().numpy().flatten().astype(np.int32)
            left_act_raw = actions_np[:num_agents].tolist()
            right_act_raw = actions_np[num_agents:].tolist()

            # 3. Managerial Tactics & Action Modulation Layer
            o_prev = raw_obs[0]
            ball_xy = np.array(o_prev['ball'][:2], dtype=np.float32)
            b_own_prev = o_prev.get('ball_owned_team', -1)
            l_pos = np.array(o_prev['left_team'][1:], dtype=np.float32)
            r_pos = np.array(o_prev['right_team'][1:], dtype=np.float32)

            left_act = apply_tactical_action_bias(
                left_act_raw, l_pos, home_anchors, home_tactics,
                team_side="left", ball_xy=ball_xy, is_team_in_possession=(b_own_prev == 0)
            )
            right_act_tactical = apply_tactical_action_bias(
                right_act_raw, -r_pos, [(-x, -y) for (x, y) in away_anchors], away_tactics,
                team_side="right", ball_xy=-ball_xy, is_team_in_possession=(b_own_prev == 1)
            )

            # 4. Action Mirror Inversion for Right Team
            right_act_mapped = [ACTION_MIRROR_MAP.get(a, a) for a in right_act_tactical]
            combined_actions = left_act + right_act_mapped

            # 5. Step Environment & Record State
            raw_next_obs, _, done, _ = env.step(combined_actions)
            if state_writer is not None:
                state_writer.append(env.get_state())

            # 6. Trajectory Recording
            o0 = raw_next_obs[0]
            l_team = np.array(o0['left_team'], dtype=np.float32)
            r_team = np.array(o0['right_team'], dtype=np.float32)
            recorded_players[step] = np.concatenate([l_team, r_team], axis=0)

            l_team_d = np.array(o0['left_team_direction'], dtype=np.float32)
            r_team_d = np.array(o0['right_team_direction'], dtype=np.float32)
            recorded_player_dirs[step] = np.concatenate([l_team_d, r_team_d], axis=0)

            recorded_balls[step] = np.array(o0['ball'], dtype=np.float32)
            recorded_ball_dirs[step] = np.array(o0['ball_direction'], dtype=np.float32)
            recorded_actions[step] = np.array(combined_actions, dtype=np.uint8)

            curr_score = [int(o0['score'][0]), int(o0['score'][1])]
            recorded_scores[step] = np.array(curr_score, dtype=np.uint8)

            if 'game_mode' not in o0 or 'ball_owned_team' not in o0 or 'ball_owned_player' not in o0:
                raise ReplayIntegrityError("GRF observation missing required fields (game_mode, ball_owned_team, ball_owned_player)")

            recorded_game_modes[step] = int(o0['game_mode'])
            recorded_owned_teams[step] = int(o0['ball_owned_team'])
            recorded_owned_players[step] = int(o0['ball_owned_player'])

            # 7. Possession & True Ball-Touch Scorer Tracking
            ball_owned = o0.get('ball_owned_team', -1)
            ball_player = o0.get('ball_owned_player', -1)

            if ball_owned == 0:
                left_poss += 1
                if ball_player >= 0:
                    last_home_touch = ball_player
            elif ball_owned == 1:
                right_poss += 1
                if ball_player >= 0:
                    last_away_touch = ball_player

            match_min = max(1, min(90, int((step / max(max_steps, 1)) * 90)))

            # 8. Rigorous Pass State Machine
            if ball_owned == 0 and ball_player >= 1 and (ball_player - 1) < len(left_act):
                p_act = left_act[ball_player - 1]
                if p_act in (9, 10, 11):
                    passes_h_att += 1
                    active_pass = {"team": 0, "passer": ball_player, "step": step}
            elif ball_owned == 1 and ball_player >= 1 and (ball_player - 1) < len(right_act_tactical):
                p_act = right_act_tactical[ball_player - 1]
                if p_act in (9, 10, 11):
                    passes_a_att += 1
                    active_pass = {"team": 1, "passer": ball_player, "step": step}

            if active_pass is not None:
                if ball_owned == active_pass["team"]:
                    if ball_player != active_pass["passer"] and ball_player >= 0:
                        if active_pass["team"] == 0:
                            passes_h_cmp += 1
                        else:
                            passes_a_cmp += 1
                        active_pass = None
                elif ball_owned != -1 and ball_owned != active_pass["team"]:
                    # Intercepted by opposition
                    active_pass = None
                elif step - active_pass["step"] > 35:
                    # Out of bounds / expired
                    active_pass = None

            # 9. Rigorous Shot & GK-Aware xG State Machine
            ball_x, ball_y = o0['ball'][0], o0['ball'][1]
            ball_vx = o0['ball_direction'][0]

            # Home team shot detection
            if 12 in left_act or (ball_owned == 0 and ball_vx > 0.12 and ball_x > 0.35):
                shots_h += 1
                shooter_idx = max(0, min(10, ball_player if ball_player >= 0 else last_home_touch))
                shooter_profile = home_roster[shooter_idx]
                away_gk_profile = away_roster[0]
                away_gk_pos = (float(r_team[0, 0]), float(r_team[0, 1]))

                shot_xg = compute_shot_xg(
                    shooter_x=ball_x, shooter_y=ball_y, goal_x=1.0,
                    defenders=r_team, shooting_attr=shooter_profile.shooting,
                    gk_pos=away_gk_pos, gk_save_coverage=away_gk_profile.gk_save_coverage
                )
                xg_h += shot_xg
                if abs(ball_y) < 0.08:
                    sot_h += 1
                active_shot = {"team": 0, "shooter": shooter_idx, "xg": shot_xg, "step": step}

            # Away team shot detection
            if 12 in right_act_tactical or (ball_owned == 1 and ball_vx < -0.12 and ball_x < -0.35):
                shots_a += 1
                shooter_idx = max(0, min(10, ball_player if ball_player >= 0 else last_away_touch))
                shooter_profile = away_roster[shooter_idx]
                home_gk_profile = home_roster[0]
                home_gk_pos = (float(l_team[0, 0]), float(l_team[0, 1]))

                shot_xg = compute_shot_xg(
                    shooter_x=ball_x, shooter_y=ball_y, goal_x=-1.0,
                    defenders=l_team, shooting_attr=shooter_profile.shooting,
                    gk_pos=home_gk_pos, gk_save_coverage=home_gk_profile.gk_save_coverage
                )
                xg_a += shot_xg
                if abs(ball_y) < 0.08:
                    sot_a += 1
                active_shot = {"team": 1, "shooter": shooter_idx, "xg": shot_xg, "step": step}

            # 10. Goal Event Detection & Scorer Attribution (Frame-Accurate)
            if curr_score[0] > last_score[0]:
                shots_h = max(shots_h, curr_score[0])
                sot_h = max(sot_h, curr_score[0])
                scorer_idx = active_shot["shooter"] if (active_shot and active_shot["team"] == 0) else last_home_touch
                scorer_idx = max(0, min(len(home_players) - 1, scorer_idx))
                scorer = home_players[scorer_idx].split('(')[0].strip()
                events.append({
                    "step": step,
                    "sim_time": round(step * 0.1, 2),
                    "minute": match_min,
                    "type": "goal",
                    "team": "home",
                    "player": scorer,
                    "score": f"{curr_score[0]}-{curr_score[1]}",
                    "details": f"Goal! {scorer} scores for {home_team}!"
                })
                last_score = list(curr_score)
                active_shot = None

            elif curr_score[1] > last_score[1]:
                shots_a = max(shots_a, curr_score[1])
                sot_a = max(sot_a, curr_score[1])
                scorer_idx = active_shot["shooter"] if (active_shot and active_shot["team"] == 1) else last_away_touch
                scorer_idx = max(0, min(len(away_players) - 1, scorer_idx))
                scorer = away_players[scorer_idx].split('(')[0].strip()
                events.append({
                    "step": step,
                    "sim_time": round(step * 0.1, 2),
                    "minute": match_min,
                    "type": "goal",
                    "team": "away",
                    "player": scorer,
                    "score": f"{curr_score[0]}-{curr_score[1]}",
                    "details": f"Goal! {scorer} scores for {away_team}!"
                })
                last_score = list(curr_score)
                active_shot = None

            raw_obs = raw_next_obs
            step += 1
    finally:
        actual_steps = step
        env.close()
        if state_writer is not None:
            state_writer.close()

    # Locate generated native dump and move to target destination if debug/record_dump was requested
    import glob, shutil
    if record_dump:
        dump_files = sorted(glob.glob(f"{match_dump_dir}/episode_done_*.dump"))
        if dump_files and trace_dump_path:
            os.makedirs(os.path.dirname(trace_dump_path), exist_ok=True)
            shutil.move(dump_files[-1], trace_dump_path)
        shutil.rmtree(match_dump_dir, ignore_errors=True)

    # Invariant guarantees
    final_score = [int(curr_score[0]), int(curr_score[1])]
    shots_h = max(shots_h, final_score[0])
    shots_a = max(shots_a, final_score[1])
    sot_h = max(sot_h, final_score[0])
    sot_a = max(sot_a, final_score[1])
    tot_poss = max(1, left_poss + right_poss)
    h_poss_pct = round((left_poss / tot_poss) * 100.0, 1)
    a_poss_pct = round(100.0 - h_poss_pct, 1)
    xg_h = max(final_score[0] * 0.35, round(xg_h, 2))
    xg_a = max(final_score[1] * 0.35, round(xg_a, 2))

    manifest = MatchManifest(
        match_id=match_id,
        home_team=home_team,
        away_team=away_team,
        home_score=final_score[0],
        away_score=final_score[1],
        score=(final_score[0], final_score[1]),
        total_steps=actual_steps,
        possession=(h_poss_pct, a_poss_pct),
        shots=(shots_h, shots_a),
        shots_on_target=(sot_h, sot_a),
        xg=(xg_h, xg_a),
        passes_attempted=(passes_h_att, passes_a_att),
        passes_completed=(passes_h_cmp, passes_a_cmp),
        events=events,
        home_players=home_players,
        away_players=away_players,
        home_formation=home_formation,
        away_formation=away_formation,
        home_color=home_color,
        away_color=away_color,
        engine_fingerprint={
            "engine": "GRF+TiKick",
            "engine_version": "2.2.0",
            "seed": seed_val,
            "feature_schema": "canonical-268-v2",
            "determinism_level": 3,
            "sim_fps": 10.0,
            "sim_step_seconds": 0.1,
            "scenario": "11_vs_11_kaggle",
            "action_set": "full",
            "state_schema": "grf_chunked_zlib_v2" if state_writer else "none",
        },
        video_url=f"/recordings/match_{match_id}.mp4",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    trajectory = MatchTrajectory(
        match_id=match_id,
        seed=seed_val,
        total_steps=actual_steps,
        player_coords=recorded_players[:actual_steps],
        player_dirs=recorded_player_dirs[:actual_steps],
        ball_coords=recorded_balls[:actual_steps],
        ball_dirs=recorded_ball_dirs[:actual_steps],
        actions=recorded_actions[:actual_steps],
        scores=recorded_scores[:actual_steps],
        manifest=manifest,
        game_mode=recorded_game_modes[:actual_steps],
        ball_owned_team=recorded_owned_teams[:actual_steps],
        ball_owned_player=recorded_owned_players[:actual_steps],
    )

    if trace_npz_path:
        trajectory.save_to_npz(Path(trace_npz_path))

    result_json = manifest.to_dict()
    result_json["trajectory_hash"] = trajectory.compute_trajectory_hash()
    return result_json


def run_daemon_server(port: int = 58210):
    """
    Persistent daemon mode: keeps TiKick PyTorch weights resident in memory
    and processes match simulation requests over a local TCP socket.
    """
    import socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(5)
    print(f"GRF_SIM_DAEMON_READY:{port}", flush=True)

    while True:
        try:
            conn, _ = server.accept()
            with conn:
                data_bytes = b""
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    data_bytes += chunk
                    if b"\n" in data_bytes:
                        break

                if not data_bytes.strip():
                    continue

                payload = json.loads(data_bytes.decode('utf-8').strip())
                if payload.get("command") == "shutdown":
                    conn.sendall(b"OK\n")
                    break

                res = run_simulation(payload)
                resp_bytes = json.dumps(res).encode('utf-8') + b"\n"
                conn.sendall(resp_bytes)
        except Exception as e:
            sys.stderr.write(f"Daemon error: {e}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 58210
        run_daemon_server(port)
    else:
        payload_str = sys.argv[1]
        if os.path.exists(payload_str):
            with open(payload_str, "r", encoding="utf-8") as f:
                args = json.load(f)
        else:
            args = json.loads(payload_str)
        res = run_simulation(args)
        print("MATCH_SIM_RESULT_JSON:" + json.dumps(res))
