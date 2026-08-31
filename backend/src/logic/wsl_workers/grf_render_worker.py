"""
WSL Dedicated Worker: Standalone 3D Broadcast & Replay Video Renderer.
Renders 720p HD broadcast videos from pre-computed .dump or .npz trajectories
with TV studio graphics, floating scoreboard HUD, slow-mo zoom replays, and studio boards.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

# Ensure backend/src and third-party modules can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_src = os.path.dirname(os.path.dirname(script_dir))
if backend_src not in sys.path:
    sys.path.insert(0, backend_src)

import cv2
import imageio
from logic.grf_trajectory import MatchTrajectory, MatchManifest
from logic.grf_renderer import (
    hex_to_bgr,
    team_color_from_name,
    draw_hud,
    draw_replay_frame,
    draw_pre_match_card,
    draw_studio_stats_card,
    render_video_from_trajectory,
    draw_pitch_frame_from_state
)


def write_progress_atomic(progress_file: Optional[str], data: Dict[str, Any]):
    """Write progress state atomically via temp file to avoid Windows/WSL read lock contention."""
    if not progress_file:
        return
    try:
        tmp_file = f"{progress_file}.tmp.{os.getpid()}"
        with open(tmp_file, "w", encoding="utf-8") as pf:
            json.dump(data, pf)
        os.replace(tmp_file, progress_file)
    except Exception:
        pass


def render_from_trajectory_npz(payload: Dict[str, Any]):
    """Render broadcast MP4 directly from immutable MatchTrajectory (.npz) file."""
    trajectory_file = payload["trajectory_file"]
    output_mp4 = payload["output_mp4"]
    progress_file = payload.get("progress_file")
    match_id = str(payload.get("match_id", "match"))

    traj = MatchTrajectory.load_from_npz(Path(trajectory_file))

    def _progress_cb(pct: int, step: int, total_steps: int, match_min: int):
        if progress_file:
            write_progress_atomic(progress_file, {
                "status": "rendering", "progress": pct, "step": step,
                "total_steps": total_steps, "match_minute": match_min,
                "stage": f"Replaying 3D Broadcast • {match_min}'/90'...",
                "score": list(traj.manifest.score), "completed": False
            })

    video_url = render_video_from_trajectory(traj, output_mp4, progress_callback=_progress_cb)

    if progress_file:
        write_progress_atomic(progress_file, {
            "status": "completed", "progress": 100, "step": traj.total_steps,
            "total_steps": traj.total_steps, "match_minute": 90,
            "stage": "3D Match Replay Complete!",
            "video_url": video_url, "score": list(traj.manifest.score), "completed": True
        })

    result = {
        "match_id": str(match_id),
        "home_team": traj.manifest.home_team,
        "away_team": traj.manifest.away_team,
        "score": list(traj.manifest.score),
        "possession": list(traj.manifest.possession),
        "shots": list(traj.manifest.shots),
        "events": traj.manifest.events,
        "video_url": video_url,
    }
    print("MATCH_RENDER_RESULT_JSON:" + json.dumps(result))


def render_from_dump(payload: Dict[str, Any]):
    from gfootball.env import script_helpers, config, football_env

    match_id = str(payload["match_id"])
    home_team = payload.get("home_team", "Home Team")
    away_team = payload.get("away_team", "Away Team")
    dump_file = payload["dump_file"]
    output_mp4 = payload["output_mp4"]
    progress_file = payload.get("progress_file")
    home_players = payload.get("home_players") or [f"{home_team} Player {i+1}" for i in range(11)]
    away_players = payload.get("away_players") or [f"{away_team} Player {i+1}" for i in range(11)]
    home_formation = payload.get("home_formation", "4-3-3")
    away_formation = payload.get("away_formation", "4-2-3-1")
    home_color = payload.get("home_color") or team_color_from_name(home_team)
    away_color = payload.get("away_color") or team_color_from_name(away_team)
    home_bgr = hex_to_bgr(home_color)
    away_bgr = hex_to_bgr(away_color)

    helper = script_helpers.ScriptHelpers()
    replay = helper.load_dump(dump_file)
    total_steps = len(replay)

    cfg = config.Config(replay[0]['debug']['config'])
    cfg['players'] = helper._ScriptHelpers__build_players(dump_file, cfg['players'])
    cfg['render_resolution_x'] = 1280
    cfg['render_resolution_y'] = 720
    cfg['real_time'] = False
    cfg['physics_steps_per_frame'] = 1

    env = football_env.FootballEnv(cfg)
    env.render()
    env.reset()

    os.makedirs(os.path.dirname(output_mp4) or '.', exist_ok=True)
    writer = imageio.get_writer(output_mp4, fps=15, codec='libx264',
                                pixelformat='yuv420p', quality=8)

    intro_card = draw_pre_match_card(
        w=1280, h=720, home_team=home_team, away_team=away_team,
        home_players=home_players, away_players=away_players,
        home_formation=home_formation, away_formation=away_formation,
        home_bgr=home_bgr, away_bgr=away_bgr
    )
    for _ in range(45):
        writer.append_data(intro_card)

    curr_score = [0, 0]
    last_score = [0, 0]
    left_poss = 0
    right_poss = 0
    shots_h = 0
    shots_a = 0
    events = []
    goal_banner = None
    goal_banner_cd = 0
    raw_replay_buffer = []
    last_scorer = None
    last_home_touch = 10
    last_away_touch = 10

    for step in range(total_steps):
        obs, rew, done, info = env.step([])
        raw_o = obs[0] if isinstance(obs, list) else obs

        curr_score = [int(raw_o['score'][0]), int(raw_o['score'][1])]
        ball_owned = raw_o.get('ball_owned_team', -1)
        ball_player = raw_o.get('ball_owned_player', -1)
        if ball_owned == 0:
            left_poss += 1
            if ball_player >= 0:
                last_home_touch = ball_player
        elif ball_owned == 1:
            right_poss += 1
            if ball_player >= 0:
                last_away_touch = ball_player

        match_min = max(1, min(90, int((step / max(total_steps, 1)) * 90)))
        is_second_half = step > (total_steps // 2)

        if curr_score[0] > last_score[0]:
            shots_h += 1
            scorer_idx = max(0, min(len(home_players) - 1, last_home_touch))
            scorer = home_players[scorer_idx].split('(')[0].strip()
            goal_banner = f"GOAL!  {scorer}  ({match_min}')"
            goal_banner_cd = 30
            last_score = list(curr_score)
            last_scorer = scorer
            events.append({
                "minute": match_min, "type": "goal", "team": "home",
                "player": scorer, "details": f"Goal! {scorer} scores for {home_team}!"
            })
        elif curr_score[1] > last_score[1]:
            shots_a += 1
            scorer_idx = max(0, min(len(away_players) - 1, last_away_touch))
            scorer = away_players[scorer_idx].split('(')[0].strip()
            goal_banner = f"GOAL!  {scorer}  ({match_min}')"
            goal_banner_cd = 30
            last_score = list(curr_score)
            last_scorer = scorer
            events.append({
                "minute": match_min, "type": "goal", "team": "away",
                "player": scorer, "details": f"Goal! {scorer} scores for {away_team}!"
            })

        frame = env.render(mode='rgb_array')
        if frame is not None:
            raw_replay_buffer.append(frame.copy())
            if len(raw_replay_buffer) > 40:
                raw_replay_buffer.pop(0)

            banner = goal_banner if goal_banner_cd > 0 else None
            annotated = draw_hud(
                frame, home_team, away_team, (curr_score[0], curr_score[1]),
                match_min, home_bgr, away_bgr, banner, is_second_half
            )
            writer.append_data(annotated)

        if progress_file and (step % 50 == 0 or step == total_steps - 1):
            pct = min(98, 5 + int((step / max(total_steps - 1, 1)) * 93))
            write_progress_atomic(progress_file, {
                "status": "rendering", "progress": pct, "step": step,
                "total_steps": total_steps, "match_minute": match_min,
                "stage": f"Replaying 3D Broadcast • {match_min}'/90'...",
                "score": curr_score, "completed": False
            })

        if done:
            break

    tot_p = max(1, left_poss + right_poss)
    motm = last_scorer or (home_players[8] if curr_score[0] >= curr_score[1] else away_players[9])
    ft_card = draw_studio_stats_card(
        w=1280, h=720, title="FULL TIME", home_team=home_team, away_team=away_team,
        score=(curr_score[0], curr_score[1]), h_poss=(left_poss / tot_p) * 100, a_poss=(right_poss / tot_p) * 100,
        h_shots=shots_h, a_shots=shots_a,
        home_bgr=home_bgr, away_bgr=away_bgr, events=events,
        motm_player=motm
    )
    for _ in range(75):
        writer.append_data(ft_card)

    writer.close()
    env.close()

    video_url = f"/recordings/{os.path.basename(output_mp4)}"
    result = {
        "match_id": str(match_id),
        "home_team": home_team, "away_team": away_team,
        "score": curr_score,
        "possession": [round((left_poss / tot_p) * 100, 1), round((right_poss / tot_p) * 100, 1)],
        "shots": [shots_h, shots_a],
        "events": events,
        "video_url": video_url,
    }
    print("MATCH_RENDER_RESULT_JSON:" + json.dumps(result))


def render_from_grf_states(payload: Dict[str, Any]):
    """
    Render 100% faithful 3D GRF broadcast video by directly restoring recorded engine states.
    Authentic 3D graphics (stadium, grass, lighting, player models, shadows, 3D ball)
    with TV broadcast scoreboard HUD, goal celebration banners, and studio cards.
    """
    import pickle
    import gfootball.env as football_env

    match_id = str(payload.get("match_id", "match"))
    states_file = payload.get("states_file")
    output_mp4 = payload["output_mp4"]
    progress_file = payload.get("progress_file")
    trajectory_file = payload.get("trajectory_file")

    traj = None
    if trajectory_file and os.path.exists(trajectory_file):
        traj = MatchTrajectory.load_from_npz(Path(trajectory_file))

    with open(states_file, 'rb') as sf:
        states = pickle.load(sf)
    total_steps = len(states)

    home_team = traj.manifest.home_team if traj else payload.get("home_team", "Home Team")
    away_team = traj.manifest.away_team if traj else payload.get("away_team", "Away Team")
    home_players = traj.manifest.home_players if traj else (payload.get("home_players") or [f"{home_team} Player {i+1}" for i in range(11)])
    away_players = traj.manifest.away_players if traj else (payload.get("away_players") or [f"{away_team} Player {i+1}" for i in range(11)])
    home_formation = traj.manifest.home_formation if traj else payload.get("home_formation", "4-3-3")
    away_formation = traj.manifest.away_formation if traj else payload.get("away_formation", "4-2-3-1")
    home_color = (traj.manifest.home_color if traj else payload.get("home_color")) or team_color_from_name(home_team)
    away_color = (traj.manifest.away_color if traj else payload.get("away_color")) or team_color_from_name(away_team)
    home_bgr = hex_to_bgr(home_color)
    away_bgr = hex_to_bgr(away_color)

    env = football_env.create_environment(
        env_name="11_vs_11_kaggle",
        representation='raw',
        render=True,
        number_of_left_players_agent_controls=10,
        number_of_right_players_agent_controls=10,
        other_config_options={
            'render_resolution_x': 1280,
            'render_resolution_y': 720
        }
    )
    env.reset()

    os.makedirs(os.path.dirname(output_mp4) or '.', exist_ok=True)
    writer = imageio.get_writer(output_mp4, fps=15, codec='libx264',
                                pixelformat='yuv420p', quality=8)

    # 1. Pre-Match Card (3 seconds = 45 frames)
    intro_card = draw_pre_match_card(
        w=1280, h=720, home_team=home_team, away_team=away_team,
        home_players=home_players, away_players=away_players,
        home_formation=home_formation, away_formation=away_formation,
        home_bgr=home_bgr, away_bgr=away_bgr
    )
    for _ in range(45):
        writer.append_data(intro_card)

    goal_events_by_step = {}
    if traj:
        for ev in traj.manifest.events:
            if ev.get("type") == "goal":
                g_min = ev.get("minute", 0)
                approx_step = int((g_min / 90.0) * total_steps)
                goal_events_by_step[approx_step] = ev

    goal_banner = None
    goal_banner_cd = 0
    replay_buffer = []

    for step in range(total_steps):
        env.set_state(states[step])
        frame = env.render(mode='rgb_array')

        if frame is None:
            continue

        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) if frame.ndim == 3 else frame

        if traj:
            state_info = traj.get_frame_state(step)
            curr_score = state_info["score"]
            match_min = state_info["match_minute"]
            is_second_half = state_info["is_second_half"]
        else:
            obs = env.observation()[0]
            curr_score = [int(obs['score'][0]), int(obs['score'][1])]
            match_min = max(1, min(90, int((step / max(total_steps, 1)) * 90)))
            is_second_half = step > (total_steps // 2)

        if step in goal_events_by_step:
            gev = goal_events_by_step[step]
            scorer = gev.get("player", "Player")
            team_str = gev.get("team", "").upper()
            goal_banner = f"GOAL!  {scorer} ({team_str})  {match_min}'"
            goal_banner_cd = 30

        banner = goal_banner if goal_banner_cd > 0 else None
        annotated = draw_hud(
            frame_bgr, home_team, away_team, (curr_score[0], curr_score[1]),
            match_min, home_bgr, away_bgr, banner, is_second_half
        )
        writer.append_data(annotated)

        replay_buffer.append(annotated)
        if len(replay_buffer) > 30:
            replay_buffer.pop(0)

        # Slow-mo Zoom Action Replay on Goals
        if step in goal_events_by_step and len(replay_buffer) >= 15:
            for _ in range(30):
                writer.append_data(annotated)
            for rf in replay_buffer[-20:]:
                replay_annotated = draw_replay_frame(
                    rf, home_team, away_team, (curr_score[0], curr_score[1]),
                    match_min, home_bgr, away_bgr, is_second_half, zoom_factor=1.35
                )
                writer.append_data(replay_annotated)
                writer.append_data(replay_annotated)

        if goal_banner_cd > 0:
            goal_banner_cd -= 1
            if goal_banner_cd == 0:
                goal_banner = None

        # Half-Time Studio Recap Card
        if step == (total_steps // 2):
            ht_card = draw_studio_stats_card(
                w=1280, h=720, title="HALF TIME", home_team=home_team, away_team=away_team,
                score=(curr_score[0], curr_score[1]),
                h_poss=traj.manifest.possession[0] if traj else 50.0,
                a_poss=traj.manifest.possession[1] if traj else 50.0,
                h_shots=traj.manifest.shots[0] if traj else 0,
                a_shots=traj.manifest.shots[1] if traj else 0,
                h_sot=traj.manifest.shots_on_target[0] if traj else 0,
                a_sot=traj.manifest.shots_on_target[1] if traj else 0,
                h_xg=traj.manifest.xg[0] if traj else 0.0,
                a_xg=traj.manifest.xg[1] if traj else 0.0,
                home_bgr=home_bgr, away_bgr=away_bgr,
                events=[e for e in (traj.manifest.events if traj else []) if e.get("minute", 0) <= 45]
            )
            for _ in range(60):
                writer.append_data(ht_card)

        if progress_file and (step % 50 == 0 or step == total_steps - 1):
            pct = min(98, 5 + int((step / max(total_steps - 1, 1)) * 93))
            write_progress_atomic(progress_file, {
                "status": "rendering", "progress": pct, "step": step,
                "total_steps": total_steps, "match_minute": match_min,
                "stage": f"Replaying 3D Broadcast • {match_min}'/90'...",
                "score": curr_score, "completed": False
            })

    # Full-Time Card
    motm = None
    if traj:
        goals = [e for e in traj.manifest.events if e.get("type") == "goal"]
        if goals:
            motm = goals[-1].get("player")
        elif home_players and away_players:
            motm = home_players[8] if curr_score[0] >= curr_score[1] else away_players[9]

    ft_card = draw_studio_stats_card(
        w=1280, h=720, title="FULL TIME", home_team=home_team, away_team=away_team,
        score=(curr_score[0], curr_score[1]),
        h_poss=traj.manifest.possession[0] if traj else 50.0,
        a_poss=traj.manifest.possession[1] if traj else 50.0,
        h_shots=traj.manifest.shots[0] if traj else 0,
        a_shots=traj.manifest.shots[1] if traj else 0,
        h_sot=traj.manifest.shots_on_target[0] if traj else 0,
        a_sot=traj.manifest.shots_on_target[1] if traj else 0,
        h_xg=traj.manifest.xg[0] if traj else 0.0,
        a_xg=traj.manifest.xg[1] if traj else 0.0,
        home_bgr=home_bgr, away_bgr=away_bgr,
        events=traj.manifest.events if traj else [],
        motm_player=motm
    )
    for _ in range(75):
        writer.append_data(ft_card)

    writer.close()
    env.close()

    video_url = f"/recordings/{os.path.basename(output_mp4)}"
    if progress_file:
        write_progress_atomic(progress_file, {
            "status": "completed", "progress": 100, "step": total_steps,
            "total_steps": total_steps, "match_minute": 90,
            "stage": "3D Match Replay Complete!",
            "video_url": video_url, "score": curr_score, "completed": True
        })

    result = {
        "match_id": str(match_id),
        "home_team": home_team, "away_team": away_team,
        "score": curr_score,
        "possession": list(traj.manifest.possession) if traj else [50.0, 50.0],
        "shots": list(traj.manifest.shots) if traj else [0, 0],
        "events": traj.manifest.events if traj else [],
        "video_url": video_url,
    }
    print("MATCH_RENDER_RESULT_JSON:" + json.dumps(result))


if __name__ == "__main__":
    payload_str = sys.argv[1]
    if os.path.exists(payload_str):
        with open(payload_str, "r", encoding="utf-8") as f:
            args = json.load(f)
    else:
        args = json.loads(payload_str)

    states_candidate = args.get("states_file")
    if not states_candidate and args.get("trajectory_file"):
        auto_states = args["trajectory_file"].replace(".npz", "_states.pkl")
        if os.path.exists(auto_states):
            states_candidate = auto_states
            args["states_file"] = states_candidate

    if states_candidate and os.path.exists(states_candidate):
        render_from_grf_states(args)
    elif args.get("trajectory_file") and os.path.exists(args["trajectory_file"]):
        render_from_trajectory_npz(args)
    elif args.get("dump_file") and os.path.exists(args["dump_file"]):
        render_from_dump(args)
    else:
        raise ValueError("Neither states_file, trajectory_file, nor dump_file found in render payload.")
