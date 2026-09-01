"""
WSL Dedicated Worker: Multi-Fixture Parallel Matchday Batch Simulator.
Executes batched TiKick GPU inference across concurrent 11v11 GRF environments.
Uses shared canonical perspective, tactical modulation, and state machines from grf_core.
"""

import os
import sys
import json
import time
import hashlib
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
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
from logic.grf_state_archive import ReplayIntegrityError
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


def run_batch_simulation(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    fixtures = payload["fixtures"]
    ckpt_path = payload["ckpt_path"]
    tikick_dir = payload.get("tikick_dir", "")
    max_steps = int(payload.get("max_steps", 1200))

    if tikick_dir and tikick_dir not in sys.path:
        sys.path.insert(0, tikick_dir)
    from tmarl.networks.policy_network import PolicyNetwork

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if torch.cuda.is_available():
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    obs_space = gym.spaces.Box(low=-1e6, high=1e6, shape=(268,), dtype='float32')
    action_space = gym.spaces.Discrete(33)
    policy = PolicyNetwork(TiKickModelConfig(), obs_space, action_space, device=device)
    state_dict = torch.load(ckpt_path, map_location=device)
    policy.load_state_dict(state_dict)
    policy.eval()

    num_matches = len(fixtures)
    envs = []
    match_states = []

    for idx, fix in enumerate(fixtures):
        m_id = str(fix["match_id"])
        seed_val = fix.get("seed_val")
        if seed_val is None:
            seed_val = int.from_bytes(hashlib.sha256(f"match_{m_id}".encode()).digest()[:4], "little")
        else:
            seed_val = int(seed_val)

        dump_path = fix.get("trace_dump")
        record_dump = bool(dump_path or fix.get("record_dump", False))
        match_dump_dir = f"/tmp/dumps/batch_{m_id}_{idx}_{int(time.time()*1000)%100000}"
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
        envs.append(env)
        raw_obs = env.reset()

        h_team = fix.get("home_team", f"Home {idx+1}")
        a_team = fix.get("away_team", f"Away {idx+1}")
        h_players = fix.get("home_players") or [f"{h_team} Player {i+1}" for i in range(11)]
        a_players = fix.get("away_players") or [f"{a_team} Player {i+1}" for i in range(11)]
        h_form = fix.get("home_formation", "4-3-3")
        a_form = fix.get("away_formation", "4-2-3-1")

        raw_h_profiles = fix.get("home_profiles")
        if raw_h_profiles and isinstance(raw_h_profiles, list):
            h_roster = [GRFPlayerProfile(**p) if isinstance(p, dict) else p for p in raw_h_profiles]
        else:
            h_roster = [FootyGRFAdapter.extract_player_profile(p, assigned_pos="GK" if i == 0 else "CM")
                        for i, p in enumerate(h_players[:11])]

        raw_a_profiles = fix.get("away_profiles")
        if raw_a_profiles and isinstance(raw_a_profiles, list):
            a_roster = [GRFPlayerProfile(**p) if isinstance(p, dict) else p for p in raw_a_profiles]
        else:
            a_roster = [FootyGRFAdapter.extract_player_profile(p, assigned_pos="GK" if i == 0 else "CM")
                        for i, p in enumerate(a_players[:11])]

        h_tac = GRFTeamTactics(
            team_name=h_team, formation=h_form if h_form in FORMATION_COORDINATES else "4-3-3",
            offensive_bias=float(fix.get("home_offensive_bias", 50.0)),
            defensive_bias=float(fix.get("home_defensive_bias", 50.0)),
            pressing_intensity=float(fix.get("home_pressing_intensity", 50.0)),
            tempo=float(fix.get("home_tempo", 50.0)), roster=h_roster
        )
        a_tac = GRFTeamTactics(
            team_name=a_team, formation=a_form if a_form in FORMATION_COORDINATES else "4-2-3-1",
            offensive_bias=float(fix.get("away_offensive_bias", 50.0)),
            defensive_bias=float(fix.get("away_defensive_bias", 50.0)),
            pressing_intensity=float(fix.get("away_pressing_intensity", 50.0)),
            tempo=float(fix.get("away_tempo", 50.0)), roster=a_roster
        )

        match_states.append({
            "match_id": m_id,
            "seed_val": seed_val,
            "home_team": h_team, "away_team": a_team,
            "home_players": h_players, "away_players": a_players,
            "home_formation": h_form, "away_formation": a_form,
            "home_tactics": h_tac, "away_tactics": a_tac,
            "home_anchors": h_tac.get_formation_anchors(is_right_team=False)[1:],
            "away_anchors": a_tac.get_formation_anchors(is_right_team=True)[1:],
            "home_color": fix.get("home_color", "#e63946"),
            "away_color": fix.get("away_color", "#2196f3"),
            "trace_npz": fix.get("trace_npz"),
            "trace_dump": dump_path,
            "record_dump": record_dump,
            "match_dump_dir": match_dump_dir,
            "raw_obs": raw_obs,
            "done": False,
            "actual_steps": None,
            "curr_score": [0, 0],
            "last_score": [0, 0],
            "left_poss": 0, "right_poss": 0,
            "shots_h": 0, "shots_a": 0,
            "sot_h": 0, "sot_a": 0,
            "xg_h": 0.0, "xg_a": 0.0,
            "passes_h_att": 0, "passes_h_cmp": 0,
            "passes_a_att": 0, "passes_a_cmp": 0,
            "last_home_touch": 10, "last_away_touch": 10,
            "active_pass": None,
            "active_shot": None,
            "events": [],
            "left_loff": np.zeros(11, dtype=np.float32),
            "left_roff": np.zeros(11, dtype=np.float32),
            "right_loff": np.zeros(11, dtype=np.float32),
            "right_roff": np.zeros(11, dtype=np.float32),
            "rec_players": np.empty((max_steps, 22, 2), dtype=np.float32),
            "rec_player_dirs": np.empty((max_steps, 22, 2), dtype=np.float32),
            "rec_balls": np.empty((max_steps, 3), dtype=np.float32),
            "rec_ball_dirs": np.empty((max_steps, 3), dtype=np.float32),
            "rec_actions": np.empty((max_steps, 20), dtype=np.uint8),
            "rec_scores": np.empty((max_steps, 2), dtype=np.uint8),
            "rec_game_modes": np.empty(max_steps, dtype=np.int8),
            "rec_owned_teams": np.empty(max_steps, dtype=np.int8),
            "rec_owned_players": np.empty(max_steps, dtype=np.int8),
        })

    total_agents = num_matches * 20
    rnn_states = torch.zeros((total_agents, 1, 256), dtype=torch.float32, device=device)
    masks = torch.ones((total_agents, 1), dtype=torch.float32, device=device)
    avail = torch.zeros((total_agents, 33), dtype=torch.float32, device=device)
    avail[:, :20] = 1.0

    batch_obs_np = np.zeros((total_agents, 268), dtype=np.float32)

    step = 0
    while step < max_steps:
        active_indices = [i for i, ms in enumerate(match_states) if not ms["done"]]
        if not active_indices:
            break

        for m_idx in active_indices:
            ms = match_states[m_idx]
            r_obs = ms["raw_obs"]
            obs_l, ms["left_loff"], ms["left_roff"] = extract_canonical_features(
                r_obs[0:10], team_side="left", num_agents=10,
                last_loff=ms["left_loff"], last_roff=ms["left_roff"]
            )
            obs_r, ms["right_loff"], ms["right_roff"] = extract_canonical_features(
                r_obs[10:20], team_side="right", num_agents=10,
                last_loff=ms["right_loff"], last_roff=ms["right_roff"]
            )
            offset = m_idx * 20
            batch_obs_np[offset:offset + 10] = obs_l
            batch_obs_np[offset + 10:offset + 20] = obs_r

        batch_obs_t = torch.from_numpy(batch_obs_np).to(device)

        with torch.inference_mode():
            actions_batch, _, rnn_states = policy(
                batch_obs_t, rnn_states, masks, avail, deterministic=True
            )

        all_actions = actions_batch.detach().cpu().numpy().reshape(-1)

        for m_idx in active_indices:
            ms = match_states[m_idx]
            start_a = m_idx * 20
            l_act_raw = all_actions[start_a:start_a + 10].tolist()
            r_act_raw = all_actions[start_a + 10:start_a + 20].tolist()

            o_prev = ms["raw_obs"][0]
            ball_xy = np.array(o_prev['ball'][:2], dtype=np.float32)
            b_own_prev = o_prev.get('ball_owned_team', -1)
            l_pos = np.array(o_prev['left_team'][1:], dtype=np.float32)
            r_pos = np.array(o_prev['right_team'][1:], dtype=np.float32)

            l_act = apply_tactical_action_bias(
                l_act_raw, l_pos, ms["home_anchors"], ms["home_tactics"],
                team_side="left", ball_xy=ball_xy, is_team_in_possession=(b_own_prev == 0)
            )
            r_act_tactical = apply_tactical_action_bias(
                r_act_raw, -r_pos, [(-x, -y) for (x, y) in ms["away_anchors"]], ms["away_tactics"],
                team_side="right", ball_xy=-ball_xy, is_team_in_possession=(b_own_prev == 1)
            )

            r_act_mapped = [ACTION_MIRROR_MAP.get(a, a) for a in r_act_tactical]
            comb_act = l_act + r_act_mapped

            raw_next, _, d, _ = envs[m_idx].step(comb_act)
            ms["done"] = d
            if d:
                if ms["actual_steps"] is None:
                    ms["actual_steps"] = step + 1
                masks[m_idx * 20:(m_idx + 1) * 20] = 0.0
            ms["raw_obs"] = raw_next

            o0 = raw_next[0]
            l_team = o0['left_team']
            r_team = o0['right_team']
            ms["rec_players"][step, :11] = l_team
            ms["rec_players"][step, 11:] = r_team

            ms["rec_player_dirs"][step, :11] = o0['left_team_direction']
            ms["rec_player_dirs"][step, 11:] = o0['right_team_direction']

            ms["rec_balls"][step] = o0['ball']
            ms["rec_ball_dirs"][step] = o0['ball_direction']
            ms["rec_actions"][step] = comb_act

            ms["curr_score"] = [int(o0['score'][0]), int(o0['score'][1])]
            ms["rec_scores"][step] = np.array(ms["curr_score"], dtype=np.uint8)

            if 'game_mode' not in o0 or 'ball_owned_team' not in o0 or 'ball_owned_player' not in o0:
                raise ReplayIntegrityError("GRF observation missing required fields (game_mode, ball_owned_team, ball_owned_player)")

            ms["rec_game_modes"][step] = int(o0['game_mode'])
            ms["rec_owned_teams"][step] = int(o0['ball_owned_team'])
            ms["rec_owned_players"][step] = int(o0['ball_owned_player'])

            b_own = o0['ball_owned_team']
            b_player = o0['ball_owned_player']
            if b_own == 0:
                ms["left_poss"] += 1
                if b_player >= 0:
                    ms["last_home_touch"] = b_player
            elif b_own == 1:
                ms["right_poss"] += 1
                if b_player >= 0:
                    ms["last_away_touch"] = b_player

            sim_time_sec = step * SIM_STEP_SECONDS
            m_min = max(1, min(90, int(sim_time_sec / 60) + 1))

            # Pass State Machine
            if b_own == 0 and b_player >= 1 and (b_player - 1) < len(l_act):
                if l_act[b_player - 1] in (9, 10, 11):
                    ms["passes_h_att"] += 1
                    ms["active_pass"] = {"team": 0, "passer": b_player, "step": step}
            elif b_own == 1 and b_player >= 1 and (b_player - 1) < len(r_act_tactical):
                if r_act_tactical[b_player - 1] in (9, 10, 11):
                    ms["passes_a_att"] += 1
                    ms["active_pass"] = {"team": 1, "passer": b_player, "step": step}

            if ms["active_pass"] is not None:
                ap = ms["active_pass"]
                if b_own == ap["team"]:
                    if b_player != ap["passer"] and b_player >= 0:
                        if ap["team"] == 0:
                            ms["passes_h_cmp"] += 1
                        else:
                            ms["passes_a_cmp"] += 1
                        ms["active_pass"] = None
                elif b_own != -1 and b_own != ap["team"]:
                    ms["active_pass"] = None
                elif step - ap["step"] > 35:
                    ms["active_pass"] = None

            # Shot & Scorer Tracking
            bx, by = o0['ball'][0], o0['ball'][1]
            bvx = o0['ball_direction'][0]
            if 12 in l_act or (b_own == 0 and bvx > 0.12 and bx > 0.35):
                ms["shots_h"] += 1
                s_idx = max(0, min(10, b_player if b_player >= 0 else ms["last_home_touch"]))
                s_prof = ms["home_tactics"].roster[s_idx]
                a_gk = ms["away_tactics"].roster[0]
                s_xg = compute_shot_xg(bx, by, 1.0, r_team, shooting_attr=s_prof.shooting,
                                       gk_pos=(float(r_team[0, 0]), float(r_team[0, 1])),
                                       gk_save_coverage=a_gk.gk_save_coverage)
                ms["xg_h"] += s_xg
                if abs(by) < 0.08:
                    ms["sot_h"] += 1
                ms["active_shot"] = {"team": 0, "shooter": s_idx, "xg": s_xg}

            if 12 in r_act_tactical or (b_own == 1 and bvx < -0.12 and bx < -0.35):
                ms["shots_a"] += 1
                s_idx = max(0, min(10, b_player if b_player >= 0 else ms["last_away_touch"]))
                s_prof = ms["away_tactics"].roster[s_idx]
                h_gk = ms["home_tactics"].roster[0]
                s_xg = compute_shot_xg(bx, by, -1.0, l_team, shooting_attr=s_prof.shooting,
                                       gk_pos=(float(l_team[0, 0]), float(l_team[0, 1])),
                                       gk_save_coverage=h_gk.gk_save_coverage)
                ms["xg_a"] += s_xg
                if abs(by) < 0.08:
                    ms["sot_a"] += 1
                ms["active_shot"] = {"team": 1, "shooter": s_idx, "xg": s_xg}

            # Goals
            if ms["curr_score"][0] > ms["last_score"][0]:
                ms["shots_h"] = max(ms["shots_h"], ms["curr_score"][0])
                ms["sot_h"] = max(ms["sot_h"], ms["curr_score"][0])
                s_idx = ms["active_shot"]["shooter"] if (ms["active_shot"] and ms["active_shot"]["team"] == 0) else ms["last_home_touch"]
                s_idx = max(0, min(len(ms["home_players"]) - 1, s_idx))
                s_name = ms["home_players"][s_idx].split('(')[0].strip()
                ms["events"].append({
                    "minute": m_min, "type": "goal", "team": "home", "player": s_name,
                    "score": f"{ms['curr_score'][0]}-{ms['curr_score'][1]}",
                    "details": f"Goal! {s_name} scores for {ms['home_team']}!"
                })
                ms["last_score"] = list(ms["curr_score"])
                ms["active_shot"] = None

            elif ms["curr_score"][1] > ms["last_score"][1]:
                ms["shots_a"] = max(ms["shots_a"], ms["curr_score"][1])
                ms["sot_a"] = max(ms["sot_a"], ms["curr_score"][1])
                s_idx = ms["active_shot"]["shooter"] if (ms["active_shot"] and ms["active_shot"]["team"] == 1) else ms["last_away_touch"]
                s_idx = max(0, min(len(ms["away_players"]) - 1, s_idx))
                s_name = ms["away_players"][s_idx].split('(')[0].strip()
                ms["events"].append({
                    "minute": m_min, "type": "goal", "team": "away", "player": s_name,
                    "score": f"{ms['curr_score'][0]}-{ms['curr_score'][1]}",
                    "details": f"Goal! {s_name} scores for {ms['away_team']}!"
                })
                ms["last_score"] = list(ms["curr_score"])
                ms["active_shot"] = None

        step += 1

    for env in envs:
        env.close()

    results = []
    import glob, shutil

    for m_idx, ms in enumerate(match_states):
        actual_steps = ms["actual_steps"] if ms["actual_steps"] is not None else step
        m_id = ms["match_id"]
        if ms["record_dump"] and os.path.exists(ms["match_dump_dir"]):
            dump_files = sorted(glob.glob(f"{ms['match_dump_dir']}/episode_done_*.dump"))
            if dump_files and ms.get("trace_dump"):
                os.makedirs(os.path.dirname(ms["trace_dump"]), exist_ok=True)
                shutil.move(dump_files[-1], ms["trace_dump"])
            shutil.rmtree(ms["match_dump_dir"], ignore_errors=True)

        f_score = [int(ms["curr_score"][0]), int(ms["curr_score"][1])]
        tot_poss = max(1, ms["left_poss"] + ms["right_poss"])
        h_poss = round((ms["left_poss"] / tot_poss) * 100.0, 1)
        a_poss = round(100.0 - h_poss, 1)

        manifest = MatchManifest(
            match_id=m_id,
            home_team=ms["home_team"], away_team=ms["away_team"],
            home_score=f_score[0], away_score=f_score[1],
            score=(f_score[0], f_score[1]),
            total_steps=actual_steps,
            possession=(h_poss, a_poss),
            shots=(max(ms["shots_h"], f_score[0]), max(ms["shots_a"], f_score[1])),
            shots_on_target=(max(ms["sot_h"], f_score[0]), max(ms["sot_a"], f_score[1])),
            xg=(max(f_score[0] * 0.35, round(ms["xg_h"], 2)), max(f_score[1] * 0.35, round(ms["xg_a"], 2))),
            passes_attempted=(ms["passes_h_att"], ms["passes_a_att"]),
            passes_completed=(ms["passes_h_cmp"], ms["passes_a_cmp"]),
            events=ms["events"],
            home_players=ms["home_players"], away_players=ms["away_players"],
            home_formation=ms["home_formation"], away_formation=ms["away_formation"],
            home_color=ms["home_color"], away_color=ms["away_color"],
            engine_fingerprint={
                "engine": "GRF+TiKick-Batch", "engine_version": "2.1.0",
                "seed": ms["seed_val"], "determinism_level": 2,
            },
            video_url=f"/recordings/match_{m_id}.mp4",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        trajectory = MatchTrajectory(
            match_id=m_id,
            seed=ms["seed_val"],
            total_steps=actual_steps,
            player_coords=ms["rec_players"][:actual_steps],
            player_dirs=ms["rec_player_dirs"][:actual_steps],
            ball_coords=ms["rec_balls"][:actual_steps],
            ball_dirs=ms["rec_ball_dirs"][:actual_steps],
            actions=ms["rec_actions"][:actual_steps],
            scores=ms["rec_scores"][:actual_steps],
            manifest=manifest,
            game_mode=ms["rec_game_modes"][:actual_steps],
            ball_owned_team=ms["rec_owned_teams"][:actual_steps],
            ball_owned_player=ms["rec_owned_players"][:actual_steps],
        )

        if ms.get("trace_npz"):
            trajectory.save_to_npz(Path(ms["trace_npz"]))

        m_dict = manifest.to_dict()
        m_dict["trajectory_hash"] = trajectory.compute_trajectory_hash()
        results.append(m_dict)

    return results


if __name__ == "__main__":
    payload_str = sys.argv[1]
    if os.path.exists(payload_str):
        with open(payload_str, "r", encoding="utf-8") as f:
            args = json.load(f)
    else:
        args = json.loads(payload_str)
    res = run_batch_simulation(args)
    print("MATCH_BATCH_SIM_RESULT_JSON:" + json.dumps(results if 'results' in locals() else res))
