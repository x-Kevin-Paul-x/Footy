"""
High-Performance Parallel Matchday Batch Simulator for Google Research Football (GRF).
Executes authentic 11v11 MARL physics across multiple concurrent fixtures with Batched TiKick GPU Inference.
Records compact .npz trajectory and event traces for 100% consistent 3D cinematic video replay.
"""

import os
import sys
import json
import time
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import numpy as np

from config import (
    RECORDINGS_DIR,
    TIKICK_CHECKPOINT_PATH,
    LOCAL_TIKICK_DIR,
    FOOTY_GRF_MAX_STEPS,
    BASE_DIR
)
from logic.grf_renderer import team_color_from_name

logger = logging.getLogger(__name__)


def to_wsl_path(win_path: Path) -> str:
    resolved = win_path.resolve()
    drive = resolved.drive.replace(":", "").lower()
    rest = str(resolved.relative_to(resolved.anchor)).replace("\\", "/")
    return f"/mnt/{drive}/{rest}"


WSL_BATCH_WORKER = r"""
import os, sys, json, time, hashlib
import numpy as np
import torch

script_dir = os.path.dirname(os.path.abspath(__file__))
backend_src = os.path.dirname(script_dir)
if backend_src not in sys.path:
    sys.path.insert(0, backend_src)

tikick_path = "{tikick_dir}"
if tikick_path not in sys.path:
    sys.path.insert(0, tikick_path)

import gym
import gfootball.env as football_env
from tmarl.networks.policy_network import PolicyNetwork
from logic.grf_core import extract_canonical_features, compute_shot_xg, ACTION_MIRROR_MAP
from logic.grf_trajectory import MatchTrajectory, MatchManifest


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


def run_batch(fixtures, ckpt_path, max_steps):
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
            seed_val = int(hashlib.sha256(f"match_{m_id}".encode()).hexdigest()[:8], 16) % 100000

        dump_path = fix.get("trace_dump") or f"/tmp/dumps/trace_{m_id}.dump"
        match_dump_dir = f"/tmp/dumps/batch_{m_id}_{idx}_{int(time.time()*1000)%100000}"
        os.makedirs(match_dump_dir, exist_ok=True)

        env = football_env.create_environment(
            env_name="11_vs_11_kaggle",
            stacked=False,
            representation='raw',
            rewards='scoring',
            write_goal_dumps=False,
            write_full_episode_dumps=True,
            render=False,
            number_of_left_players_agent_controls=10,
            number_of_right_players_agent_controls=10,
            other_config_options={
                'action_set': 'full',
                'random_seed': seed_val,
                'tracesdir': match_dump_dir,
                'dump_full_episodes': True,
            }
        )
        envs.append(env)

        h_team = fix["home_team"]
        a_team = fix["away_team"]
        hp = fix.get("home_players") or [f"{h_team} Player {i+1}" for i in range(11)]
        ap = fix.get("away_players") or [f"{a_team} Player {i+1}" for i in range(11)]

        match_states.append({
            "match_id": m_id,
            "seed_val": seed_val,
            "home_team": h_team,
            "away_team": a_team,
            "home_players": hp,
            "away_players": ap,
            "home_formation": fix.get("home_formation", "4-3-3"),
            "away_formation": fix.get("away_formation", "4-2-3-1"),
            "home_color": fix.get("home_color", "#e63946"),
            "away_color": fix.get("away_color", "#2196f3"),
            "trace_dump": dump_path,
            "dump_dir": match_dump_dir,
            "trace_npz": fix.get("trace_npz"),
            "loff_l": None, "roff_l": None,
            "loff_r": None, "roff_r": None,
            "last_score": [0, 0],
            "curr_score": [0, 0],
            "last_home_touch": 10,
            "last_away_touch": 10,
            "events": [],
            "left_poss": 0, "right_poss": 0,
            "shots_l": 0, "shots_r": 0,
            "sot_l": 0, "sot_r": 0,
            "xg_l": 0.0, "xg_r": 0.0,
            "done": False,
            "recorded_players": np.empty((max_steps, 22, 2), dtype=np.float32),
            "recorded_player_dirs": np.empty((max_steps, 22, 2), dtype=np.float32),
            "recorded_balls": np.empty((max_steps, 3), dtype=np.float32),
            "recorded_ball_dirs": np.empty((max_steps, 3), dtype=np.float32),
            "recorded_actions": np.empty((max_steps, 20), dtype=np.uint8),
            "recorded_scores": np.empty((max_steps, 2), dtype=np.uint8),
        })

    raw_obs_list = [env.reset() for env in envs]
    total_agents = num_matches * 20

    rnn_states = torch.zeros(total_agents, 1, 256, device=device)
    masks = torch.ones(total_agents, 1, device=device)
    avail_actions = torch.zeros(total_agents, 33, device=device)
    avail_actions[:, :20] = 1.0

    step = 0
    all_done = False

    while not all_done and step < max_steps:
        batch_obs = []
        for i in range(num_matches):
            st = match_states[i]
            if st["done"]:
                batch_obs.append(np.zeros((20, 268), dtype=np.float32))
                continue

            ro = raw_obs_list[i]
            obs_l, st["loff_l"], st["roff_l"] = extract_canonical_features(
                ro[0:10], team_side="left", num_agents=10,
                last_loff=st["loff_l"], last_roff=st["roff_l"]
            )
            obs_r, st["loff_r"], st["roff_r"] = extract_canonical_features(
                ro[10:20], team_side="right", num_agents=10,
                last_loff=st["loff_r"], last_roff=st["roff_r"]
            )
            batch_obs.append(np.concatenate([obs_l, obs_r], axis=0))

        obs_batch_np = np.concatenate(batch_obs, axis=0)
        obs_batch_t = torch.from_numpy(obs_batch_np).to(device)

        with torch.inference_mode():
            actions_batch, _, rnn_states = policy(
                obs_batch_t, rnn_states, masks, avail_actions, deterministic=True
            )

        act_matrix = actions_batch.cpu().numpy().reshape(num_matches, 20).astype(np.int32)
        all_done = True

        for i in range(num_matches):
            st = match_states[i]
            if st["done"]:
                continue

            all_done = False
            act_i = act_matrix[i]
            left_act = act_i[:10].tolist()
            right_act = [ACTION_MIRROR_MAP.get(a, a) for a in act_i[10:].tolist()]
            combined_act = left_act + right_act

            raw_next_obs, _, done, _ = envs[i].step(combined_act)
            if done:
                st["done"] = True

            o0 = raw_next_obs[0]
            st["recorded_players"][step] = np.concatenate([o0['left_team'], o0['right_team']], axis=0)
            st["recorded_player_dirs"][step] = np.concatenate([o0['left_team_direction'], o0['right_team_direction']], axis=0)
            st["recorded_balls"][step] = np.array(o0['ball'], dtype=np.float32)
            st["recorded_ball_dirs"][step] = np.array(o0['ball_direction'], dtype=np.float32)
            st["recorded_actions"][step] = np.array(combined_act, dtype=np.uint8)

            curr = [int(o0['score'][0]), int(o0['score'][1])]
            st["curr_score"] = curr
            st["recorded_scores"][step] = np.array(curr, dtype=np.uint8)

            ball_owned = o0.get('ball_owned_team', -1)
            ball_player = o0.get('ball_owned_player', -1)
            if ball_owned == 0:
                st["left_poss"] += 1
                if ball_player >= 0: st["last_home_touch"] = ball_player
            elif ball_owned == 1:
                st["right_poss"] += 1
                if ball_player >= 0: st["last_away_touch"] = ball_player

            match_min = max(1, min(90, int((step / max_steps) * 90)))

            if curr[0] > st["last_score"][0]:
                p_idx = max(0, min(len(st["home_players"]) - 1, st["last_home_touch"]))
                scorer = st["home_players"][p_idx].split('(')[0].strip()
                st["events"].append({
                    "minute": match_min, "type": "goal", "team": "home",
                    "player": scorer, "details": f"Goal! {scorer} scores for {st['home_team']}!"
                })
                st["shots_l"] = max(st["shots_l"] + 1, curr[0])
                st["sot_l"] = max(st["sot_l"] + 1, curr[0])
                st["last_score"] = list(curr)
            elif curr[1] > st["last_score"][1]:
                p_idx = max(0, min(len(st["away_players"]) - 1, st["last_away_touch"]))
                scorer = st["away_players"][p_idx].split('(')[0].strip()
                st["events"].append({
                    "minute": match_min, "type": "goal", "team": "away",
                    "player": scorer, "details": f"Goal! {scorer} scores for {st['away_team']}!"
                })
                st["shots_r"] = max(st["shots_r"] + 1, curr[1])
                st["sot_r"] = max(st["sot_r"] + 1, curr[1])
                st["last_score"] = list(curr)

            raw_obs_list[i] = raw_next_obs

        step += 1

    for env in envs:
        env.close()

    import glob, shutil
    results = []
    for st in match_states:
        final_score = [int(st["curr_score"][0]), int(st["curr_score"][1])]
        total_p = max(1, st["left_poss"] + st["right_poss"])
        h_poss = round((st["left_poss"] / total_p) * 100.0, 1)
        a_poss = round(100.0 - h_poss, 1)

        target_dump = st["trace_dump"]
        dump_files = sorted(glob.glob(f"{st['dump_dir']}/episode_done_*.dump"))
        if dump_files and target_dump:
            os.makedirs(os.path.dirname(target_dump), exist_ok=True)
            shutil.move(dump_files[-1], target_dump)
        shutil.rmtree(st["dump_dir"], ignore_errors=True)

        manifest = MatchManifest(
            match_id=st["match_id"],
            home_team=st["home_team"],
            away_team=st["away_team"],
            home_score=final_score[0],
            away_score=final_score[1],
            score=(final_score[0], final_score[1]),
            total_steps=step,
            possession=(h_poss, a_poss),
            shots=(max(final_score[0], st["shots_l"]), max(final_score[1], st["shots_r"])),
            shots_on_target=(max(final_score[0], st["sot_l"]), max(final_score[1], st["sot_r"])),
            xg=(max(final_score[0] * 0.45, round(st["xg_l"], 2)), max(final_score[1] * 0.45, round(st["xg_r"], 2))),
            events=st["events"],
            home_players=st["home_players"],
            away_players=st["away_players"],
            home_formation=st["home_formation"],
            away_formation=st["away_formation"],
            home_color=st["home_color"],
            away_color=st["away_color"],
            engine_fingerprint={
                "engine": "GRF+TiKick",
                "engine_version": "2.0.0",
                "seed": st["seed_val"],
                "batch_mode": True,
            },
            video_url=f"/recordings/match_{st['match_id']}.mp4",
        )

        if st.get("trace_npz"):
            trajectory = MatchTrajectory(
                match_id=st["match_id"],
                seed=st["seed_val"],
                total_steps=step,
                player_coords=st["recorded_players"][:step],
                player_dirs=st["recorded_player_dirs"][:step],
                ball_coords=st["recorded_balls"][:step],
                ball_dirs=st["recorded_ball_dirs"][:step],
                actions=st["recorded_actions"][:step],
                scores=st["recorded_scores"][:step],
                manifest=manifest,
            )
            trajectory.save_to_npz(Path(st["trace_npz"]))

        results.append(manifest.to_dict())

    print("MATCHDAY_BATCH_RESULTS_JSON:" + json.dumps(results))


if __name__ == "__main__":
    payload_str = sys.argv[1]
    if os.path.exists(payload_str):
        with open(payload_str, "r", encoding="utf-8") as f:
            args = json.load(f)
    else:
        args = json.loads(payload_str)
    run_batch(
        fixtures=args["fixtures"],
        ckpt_path=args["ckpt_path"],
        max_steps=args.get("max_steps", 1200)
    )
"""


class GRFBatchRunner:
    def __init__(self):
        self.wsl_python = "/root/venv_baller/bin/python3"
        self.local_ckpt = TIKICK_CHECKPOINT_PATH
        self.local_tikick = LOCAL_TIKICK_DIR
        self.max_steps = FOOTY_GRF_MAX_STEPS

    _cached_available = None
    _last_check_time = 0.0

    def is_available(self, force_recheck: bool = False) -> bool:
        now = time.time()
        if not force_recheck and GRFBatchRunner._cached_available is not None and (now - GRFBatchRunner._last_check_time) < 60.0:
            return GRFBatchRunner._cached_available
        try:
            res = subprocess.run(
                ["wsl", "-u", "root", self.wsl_python, "-c",
                 "import gfootball, torch; print('OK')"],
                capture_output=True, text=True, timeout=10
            )
            GRFBatchRunner._cached_available = "OK" in res.stdout
            GRFBatchRunner._last_check_time = now
            return GRFBatchRunner._cached_available
        except Exception:
            GRFBatchRunner._cached_available = False
            GRFBatchRunner._last_check_time = now
            return False

    def run_matchday(
        self,
        fixtures: List[Dict[str, Any]],
        max_steps: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        steps = max_steps or self.max_steps

        wsl_fixtures = []
        for fix in fixtures:
            m_id = str(fix["match_id"])
            npz_win = RECORDINGS_DIR / f"trace_{m_id}.npz"
            dump_win = RECORDINGS_DIR / f"trace_{m_id}.dump"
            wsl_fixtures.append({
                "match_id": m_id,
                "home_team": fix.get("home_team", "Home"),
                "away_team": fix.get("away_team", "Away"),
                "home_players": fix.get("home_players"),
                "away_players": fix.get("away_players"),
                "home_formation": fix.get("home_formation", "4-3-3"),
                "away_formation": fix.get("away_formation", "4-2-3-1"),
                "home_color": fix.get("home_color") or team_color_from_name(fix.get("home_team", "Home")),
                "away_color": fix.get("away_color") or team_color_from_name(fix.get("away_team", "Away")),
                "trace_npz": to_wsl_path(npz_win),
                "trace_dump": to_wsl_path(dump_win),
                "seed_val": fix.get("seed_val"),
            })

        tikick_wsl = to_wsl_path(self.local_tikick)
        ckpt_wsl = to_wsl_path(self.local_ckpt)
        worker_content = WSL_BATCH_WORKER.replace("{tikick_dir}", tikick_wsl)

        worker_win = RECORDINGS_DIR / f"run_batch_worker_{int(time.time()*1000)%100000}.py"
        payload_win = RECORDINGS_DIR / f"batch_payload_{int(time.time()*1000)%100000}.json"

        try:
            worker_win.write_text(worker_content, encoding="utf-8")
            payload_win.write_text(json.dumps({
                "fixtures": wsl_fixtures,
                "ckpt_path": ckpt_wsl,
                "max_steps": steps,
            }), encoding="utf-8")

            cmd = [
                "wsl", "-u", "root", self.wsl_python,
                to_wsl_path(worker_win), to_wsl_path(payload_win)
            ]

            logger.info("GRF Batch Runner: executing %d fixtures in parallel", len(fixtures))
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if "MATCHDAY_BATCH_RESULTS_JSON:" in res.stdout:
                json_str = res.stdout.split("MATCHDAY_BATCH_RESULTS_JSON:")[1].splitlines()[0]
                return json.loads(json_str)

            logger.error("GRF Batch Runner error:\nSTDOUT: %s\nSTDERR: %s", res.stdout, res.stderr)
            raise RuntimeError(f"Batch simulation failed: {res.stderr or res.stdout}")

        finally:
            for f in (worker_win, payload_win):
                try:
                    if f.exists():
                        f.unlink()
                except Exception:
                    pass

    def simulate(
        self,
        home_team: Any,
        away_team: Any,
        max_steps: Optional[int] = None,
        render_video: bool = False,
        match_id: Optional[str] = None
    ) -> Dict[str, Any]:
        h_name = getattr(home_team, "name", str(home_team))
        a_name = getattr(away_team, "name", str(away_team))
        fixtures = [{
            "match_id": match_id or f"match_{int(time.time()*1000)%100000}",
            "home_team": h_name,
            "away_team": a_name,
        }]
        results = self.run_matchday(fixtures, max_steps=max_steps)
        return results[0]
