"""
Native Google Research Football (GRF) 3D Simulation & Video Replay Bridge.
Executes 11v11 MARL matches with TiKick actor weights (actor.pt) via WSL2 / Docker.
Synchronizes 3D OpenGL frame rendering with canonical match scores, scorers, and timeline events at broadcast FPS.
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

from config import (
    RECORDINGS_DIR,
    TIKICK_CHECKPOINT_PATH,
    LOCAL_TIKICK_DIR
)

logger = logging.getLogger(__name__)

# Script executed inside WSL Linux environment to run GRF + TiKick
WSL_GRF_SCRIPT = """
import os
import sys
import json
import hashlib
import numpy as np
import torch
import cv2

# Ensure TiKick import path
tikick_path = "{tikick_dir}"
if tikick_path not in sys.path:
    sys.path.insert(0, tikick_path)

import gfootball.env as football_env
from tmarl.networks.policy_network import PolicyNetwork
import gym

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

def load_tikick(ckpt_path, device='cuda' if torch.cuda.is_available() else 'cpu'):
    obs_space = gym.spaces.Box(low=-1e6, high=1e6, shape=(268,), dtype='float32')
    action_space = gym.spaces.Discrete(33)
    policy = PolicyNetwork(TiKickModelConfig(), obs_space, action_space, device=torch.device(device))
    state_dict = torch.load(ckpt_path, map_location=device)
    policy.load_state_dict(state_dict)
    policy.eval()
    return policy, device

def extract_features_268(raw_obs, num_agents=10, last_loffside=None, last_roffside=None):
    if last_loffside is None:
        last_loffside = np.zeros(11, dtype=np.float32)
    if last_roffside is None:
        last_roffside = np.zeros(11, dtype=np.float32)

    ally = np.array(raw_obs[0]['left_team'])
    ally_d = np.array(raw_obs[0]['left_team_direction'])
    enemy = np.array(raw_obs[0]['right_team'])
    enemy_d = np.array(raw_obs[0]['right_team_direction'])

    ball = np.array(raw_obs[0]['ball'][:2])
    if raw_obs[0]['game_mode'] != 0:
        loffside = np.zeros(11, dtype=np.float32)
        roffside = np.zeros(11, dtype=np.float32)
    else:
        effective_ownball_team = raw_obs[0]['ball_owned_team']
        effective_ownball_player = raw_obs[0]['ball_owned_player']
        if effective_ownball_team == -1:
            ally_dist = np.linalg.norm(ball - ally, axis=-1)
            enemy_dist = np.linalg.norm(ball - enemy, axis=-1)
            if np.min(ally_dist) < np.min(enemy_dist) and np.min(ally_dist) < 0.017:
                effective_ownball_team = 0
                effective_ownball_player = np.argmin(ally_dist)
            elif np.min(enemy_dist) < np.min(ally_dist) and np.min(enemy_dist) < 0.017:
                effective_ownball_team = 1
                effective_ownball_player = np.argmin(enemy_dist)

        if effective_ownball_team == 0:
            right_xs = np.sort([raw_obs[0]['right_team'][k][0] for k in range(1, 11)])
            loffside = np.zeros(11, dtype=np.float32)
            for k in range(1, 11):
                if raw_obs[0]['left_team'][k][0] > right_xs[-1] and k != effective_ownball_player and raw_obs[0]['left_team'][k][0] > 0.0:
                    loffside[k] = 1.0
            roffside = last_roffside
        elif effective_ownball_team == 1:
            left_xs = np.sort([raw_obs[0]['left_team'][k][0] for k in range(1, 11)])
            roffside = np.zeros(11, dtype=np.float32)
            for k in range(1, 11):
                if raw_obs[0]['right_team'][k][0] < left_xs[0] and k != effective_ownball_player and raw_obs[0]['right_team'][k][0] < 0.0:
                    roffside[k] = 1.0
            loffside = last_loffside
        else:
            loffside, roffside = last_loffside, last_roffside

    obs = []
    for a in range(num_agents):
        me = ally[int(raw_obs[a]['active'])]
        ball_xy = raw_obs[a]['ball'][:2]
        ball_dist = min(1.0, float(np.linalg.norm(me - ball_xy)))
        enemy_dist = np.linalg.norm(me - enemy, axis=-1)
        to_enemy = (enemy - me).copy()
        to_ally = (ally - me).copy()
        to_ball = (ball_xy - me).copy()

        o = []
        o.extend(ally.flatten())
        o.extend(ally_d.flatten())
        o.extend(enemy.flatten())
        o.extend(enemy_d.flatten())
        o.extend(raw_obs[a]['ball'])
        o.extend(raw_obs[a]['ball_direction'])

        owned = raw_obs[a]['ball_owned_team']
        o.extend([1, 0, 0] if owned == -1 else ([0, 1, 0] if owned == 0 else [0, 0, 1]))

        active = [0] * 11
        active[raw_obs[a]['active']] = 1
        o.extend(active)

        game_mode = [0] * 7
        game_mode[raw_obs[a]['game_mode']] = 1
        o.extend(game_mode)

        o.extend(raw_obs[a]['sticky_actions'][:10])
        o.append(ball_dist)
        o.extend(raw_obs[a]['left_team_tired_factor'])
        o.extend(raw_obs[a]['left_team_yellow_card'])
        o.extend(raw_obs[a]['left_team_active'])
        o.extend(loffside)
        o.extend(roffside)
        o.extend(enemy_dist)

        to_ally[:, 0] /= 2.0
        o.extend(to_ally.flatten())
        to_enemy[:, 0] /= 2.0
        o.extend(to_enemy.flatten())
        to_ball[0] /= 2.0
        o.extend(to_ball.flatten())

        steps_left = raw_obs[a]['steps_left']
        o.append(float(steps_left) / 3001.0)
        if steps_left > 1500:
            steps_left -= 1501
        o.append(min(float(steps_left), 300.0) / 300.0)

        score_ratio = (raw_obs[a]['score'][0] - raw_obs[a]['score'][1]) / 5.0
        score_ratio = max(-1.0, min(1.0, score_ratio))
        o.append(score_ratio)

        o.extend([0.0] * 27)
        obs.append(o)

    return np.array(obs, dtype=np.float32), loffside, roffside

def run_match(match_id, home_team, away_team, render_video, max_steps, output_mp4, ckpt_path, progress_file, target_events=None, target_score=None):
    try:
        with open(progress_file, "w") as pf:
            json.dump({
                "status": "initializing",
                "progress": 5,
                "step": 0,
                "total_steps": max_steps,
                "match_minute": 0,
                "stage": "Loading TiKick 11v11 MARL Neural Policy & Initializing Pitch...",
                "completed": False
            }, pf)
    except Exception:
        pass

    policy, device = load_tikick(ckpt_path)
    
    seed_val = int(hashlib.md5(str(match_id).encode()).hexdigest()[:8], 16) % 100000
    np.random.seed(seed_val)
    torch.manual_seed(seed_val)

    num_agents = 10
    env = football_env.create_environment(
        env_name="11_vs_11_kaggle",
        stacked=False,
        representation='raw',
        rewards='scoring',
        write_goal_dumps=False,
        write_full_episode_dumps=False,
        render=render_video,
        number_of_left_players_agent_controls=num_agents,
        number_of_right_players_agent_controls=0,
        other_config_options={'action_set': 'full'}
    )

    raw_obs = env.reset()
    rnn_states = torch.zeros(num_agents, 1, 256, device=device)
    masks = torch.ones(num_agents, 1, device=device)
    avail_actions = torch.zeros(num_agents, 33, device=device)
    avail_actions[:, :20] = 1.0

    # Parse Canonical Events and Goals
    canonical_goals = []
    if target_events:
        for evt in target_events:
            e_type = (evt.get("type") or "").lower()
            e_desc = (evt.get("details") or "").lower()
            if e_type == "goal" or "goal" in e_desc or "scores" in e_desc:
                t_str = str(evt.get("team") or "").lower()
                is_home = (t_str == "home" or home_team.lower() in t_str or home_team.lower() in str(evt.get("team_name", "")).lower())
                canonical_goals.append({
                    "minute": int(evt.get("minute", 0)),
                    "team": "home" if is_home else "away",
                    "player": evt.get("player") or (f"{home_team} Scorer" if is_home else f"{away_team} Scorer")
                })
        canonical_goals.sort(key=lambda x: x["minute"])

    video_writer = None
    if render_video:
        import imageio
        os.makedirs(os.path.dirname(output_mp4), exist_ok=True)
        # Broadcast standard 12 FPS for smooth, natural TV-style action pace
        video_writer = imageio.get_writer(output_mp4, fps=12, codec='libx264', pixelformat='yuv420p', quality=8)

    done = False
    step = 0
    events = []
    left_poss_steps = 0
    right_poss_steps = 0
    total_shots_left = 0
    total_shots_right = 0
    last_loffside = None
    last_roffside = None
    last_rendered_goal_min = -1

    while not done and step < max_steps:
        obs_vec, last_loffside, last_roffside = extract_features_268(
            raw_obs, num_agents=num_agents, last_loffside=last_loffside, last_roffside=last_roffside
        )
        obs_t = torch.tensor(obs_vec, dtype=torch.float32, device=device)

        with torch.no_grad():
            actions, _, next_rnn_states = policy(
                obs_t, rnn_states, masks, avail_actions, deterministic=True
            )

        act_list = actions.cpu().numpy().flatten().astype(np.int32).tolist()
        raw_next_obs, rewards, done, info = env.step(act_list)

        curr_score = raw_next_obs[0]['score']
        ball_owned = raw_next_obs[0]['ball_owned_team']
        if ball_owned == 0:
            left_poss_steps += 1
        elif ball_owned == 1:
            right_poss_steps += 1

        match_min = int((step / max_steps) * 90)

        # Synchronize Score with Canonical Events
        active_goal_banner = None
        if canonical_goals:
            h_count = sum(1 for g in canonical_goals if g["team"] == "home" and g["minute"] <= match_min)
            a_count = sum(1 for g in canonical_goals if g["team"] == "away" and g["minute"] <= match_min)
            display_score = [h_count, a_count]

            # Check if a canonical goal occurs at current minute
            recent_goal = next((g for g in canonical_goals if g["minute"] == match_min), None)
            if recent_goal:
                active_goal_banner = f"GOAL! {recent_goal['player']} ({recent_goal['minute']}')"
        else:
            display_score = [int(curr_score[0]), int(curr_score[1])]

        # Half-Time Break Logic at 45'
        if step == (max_steps // 2):
            if render_video and video_writer is not None:
                ht_frame = env.render(mode='rgb_array')
                if ht_frame is not None:
                    ht_annotated = ht_frame.copy()
                    h_img, w_img = ht_annotated.shape[:2]
                    cv2.rectangle(ht_annotated, (0, 0), (w_img, 95), (12, 18, 28), -1)
                    ht_title = "HALF TIME"
                    cv2.putText(ht_annotated, ht_title, (int(w_img/2 - 80), 36), cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 240, 255), 2)
                    ht_score_str = f"{home_team.upper()}  {display_score[0]} - {display_score[1]}  {away_team.upper()}"
                    cv2.putText(ht_annotated, ht_score_str, (int(w_img/2 - 210), 75), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2)
                    for _ in range(16):
                        video_writer.append_data(ht_annotated)

        # Broadcast frame sampling: record every 3rd step or whenever a goal happens
        if render_video and video_writer is not None and (step % 3 == 0 or active_goal_banner is not None):
            frame = env.render(mode='rgb_array')
            if frame is not None:
                annotated = frame.copy()
                h_img, w_img = annotated.shape[:2]
                
                # Overlay Scoreboard Header
                cv2.rectangle(annotated, (0, 0), (w_img, 65), (15, 20, 30), -1)
                score_str = f"{home_team.upper()}  {display_score[0]} - {display_score[1]}  {away_team.upper()}"
                cv2.putText(annotated, score_str, (int(w_img/2 - 200), 32), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2)
                half_tag = "1st Half" if step <= (max_steps // 2) else "2nd Half"
                clock_str = f"{half_tag} | {match_min:02d}:00"
                cv2.putText(annotated, clock_str, (w_img - 170, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (245, 180, 50), 2)
                
                # Goal Highlight Banner
                if active_goal_banner:
                    cv2.rectangle(annotated, (int(w_img/2 - 260), h_img - 60), (int(w_img/2 + 260), h_img - 15), (16, 185, 129), -1)
                    cv2.putText(annotated, active_goal_banner, (int(w_img/2 - 240), h_img - 28), cv2.FONT_HERSHEY_DUPLEX, 0.68, (255, 255, 255), 2)
                    if match_min != last_rendered_goal_min:
                        last_rendered_goal_min = match_min
                        # Write 10 frames of goal highlight celebration
                        for _ in range(10):
                            video_writer.append_data(annotated)
                    else:
                        video_writer.append_data(annotated)
                else:
                    video_writer.append_data(annotated)

        step += 1
        raw_obs = raw_next_obs
        rnn_states = next_rnn_states

        # Write progress every 25 steps
        if step % 25 == 0 or step == max_steps:
            pct = min(98, 5 + int((step / max_steps) * 93))
            half_desc = "1st Half" if step <= (max_steps // 2) else "2nd Half"
            stage_msg = "Half Time Intermission (45') • Teams Switching..." if step == (max_steps // 2) else f"Rendering 3D Camera • {half_desc} (Minute {match_min}'/90')..."
            try:
                with open(progress_file, "w") as pf:
                    json.dump({
                        "status": "rendering" if render_video else "simulating",
                        "progress": pct,
                        "step": step,
                        "total_steps": max_steps,
                        "match_minute": match_min,
                        "stage": stage_msg,
                        "score": [int(display_score[0]), int(display_score[1])],
                        "completed": False
                    }, pf)
            except Exception:
                pass

    if video_writer is not None:
        video_writer.close()
    env.close()

    final_score = target_score if target_score else (display_score if canonical_goals else [int(curr_score[0]), int(curr_score[1])])
    total_poss = max(1, left_poss_steps + right_poss_steps)
    h_poss = round((left_poss_steps / total_poss) * 100, 1)
    a_poss = round(100 - h_poss, 1)

    video_rel_url = f"/recordings/{os.path.basename(output_mp4)}" if render_video else None

    # Write final completed status
    try:
        with open(progress_file, "w") as pf:
            json.dump({
                "status": "completed",
                "progress": 100,
                "step": max_steps,
                "total_steps": max_steps,
                "match_minute": 90,
                "stage": "3D Replay Render Complete!",
                "video_url": video_rel_url,
                "score": [int(final_score[0]), int(final_score[1])],
                "completed": True
            }, pf)
    except Exception:
        pass

    result = {
        "match_id": str(match_id),
        "home_team": home_team,
        "away_team": away_team,
        "score": final_score,
        "possession": [h_poss, a_poss],
        "shots": [max(final_score[0], total_shots_left), max(final_score[1], total_shots_right)],
        "events": target_events if target_events else events,
        "video_url": video_rel_url
    }
    print("MATCH_RESULT_JSON:" + json.dumps(result))

if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    run_match(
        match_id=args["match_id"],
        home_team=args["home_team"],
        away_team=args["away_team"],
        render_video=args["render_video"],
        max_steps=args["max_steps"],
        output_mp4=args["output_mp4"],
        ckpt_path=args["ckpt_path"],
        progress_file=args["progress_file"],
        target_events=args.get("target_events"),
        target_score=args.get("target_score")
    )
"""

def to_wsl_path(win_path: Path) -> str:
    resolved = win_path.resolve()
    drive = resolved.drive.replace(":", "").lower()
    rest = str(resolved.relative_to(resolved.anchor)).replace("\\", "/")
    return f"/mnt/{drive}/{rest}"

class GRFNativeRunner:
    def __init__(self):
        self.wsl_python = "/root/venv_baller/bin/python3"
        self.local_ckpt = TIKICK_CHECKPOINT_PATH
        self.local_tikick = LOCAL_TIKICK_DIR

    def is_available(self) -> bool:
        try:
            res = subprocess.run(
                ["wsl", "-u", "root", self.wsl_python, "-c", "import gfootball, torch; print('OK')"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return "OK" in res.stdout
        except Exception:
            return False

    def run_match(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        render_video: bool = False,
        max_steps: int = 3000,
        target_events: Optional[List[Dict[str, Any]]] = None,
        target_score: Optional[Tuple[int, int]] = None
    ) -> Dict[str, Any]:
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"match_{match_id}.mp4" if not str(match_id).startswith("match_") else f"{match_id}.mp4"
        output_mp4_win = RECORDINGS_DIR / filename
        output_mp4_wsl = to_wsl_path(output_mp4_win)
        ckpt_wsl = to_wsl_path(self.local_ckpt)
        tikick_wsl = to_wsl_path(self.local_tikick)

        prog_file_win = RECORDINGS_DIR / f"progress_{match_id}.json"
        prog_file_wsl = to_wsl_path(prog_file_win)

        script_content = WSL_GRF_SCRIPT.replace("{tikick_dir}", tikick_wsl)
        script_file_win = RECORDINGS_DIR / f"run_grf_{match_id}.py"
        script_file_win.write_text(script_content, encoding="utf-8")
        script_file_wsl = to_wsl_path(script_file_win)

        match_args = {
            "match_id": str(match_id),
            "home_team": home_team,
            "away_team": away_team,
            "render_video": render_video,
            "max_steps": max_steps,
            "output_mp4": output_mp4_wsl,
            "ckpt_path": ckpt_wsl,
            "progress_file": prog_file_wsl,
            "target_events": target_events,
            "target_score": list(target_score) if target_score else None
        }
        args_json = json.dumps(match_args)

        cmd = [
            "wsl", "-u", "root", "bash", "-c",
            f'xvfb-run -a -s "-screen 0 1280x720x24" {self.wsl_python} {script_file_wsl} \'{args_json}\''
        ]

        logger.info("Executing native GRF 3D simulation for match %s (render_video=%s, max_steps=%d)...", match_id, render_video, max_steps)
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        # Cleanup runner script
        try:
            if script_file_win.exists():
                script_file_win.unlink()
        except Exception:
            pass

        if "MATCH_RESULT_JSON:" in res.stdout:
            json_str = res.stdout.split("MATCH_RESULT_JSON:")[1].splitlines()[0]
            return json.loads(json_str)

        logger.error("GRF Native Runner output error: %s\nStderr: %s", res.stdout, res.stderr)
        raise RuntimeError(f"Native GRF 3D execution failed: {res.stderr or res.stdout}")
