"""
WSL Dedicated Worker: Autonomous High-Fidelity Match Video Renderer.
Renders broadcast-quality 720p/1080p MP4 videos from:
1. State Archives (.grfstate) with Next-Gen ReplayPipeline & NVENC hardware acceleration
2. Canonical Trajectories (.npz) with 2D radar/pitch compositing
3. Native GRF Episode Dumps (.dump) with 3D engine playback
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure backend/src is on sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_src = os.path.dirname(os.path.dirname(script_dir))
if backend_src not in sys.path:
    sys.path.insert(0, backend_src)

from logic.replay.replay_pipeline import ReplayPipeline
from logic.grf_trajectory import MatchTrajectory
from logic.grf_renderer import (
    render_video_from_trajectory,
    team_color_from_name,
    hex_to_bgr,
    draw_pre_match_card,
    draw_half_time_card,
    draw_full_time_card,
    draw_hud
)


def write_progress_atomic(progress_file: str, data: dict):
    tmp_file = f"{progress_file}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp_file, progress_file)


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
        "requested_render_mode": payload.get("mode", "2d"),
        "render_mode_used": "2d",
        "render_source": "trajectory_npz",
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
    """Render broadcast MP4 from native GRF .dump recording."""
    from gfootball.env import script_helpers, config, football_env
    import imageio

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
            events.append({
                "minute": match_min, "step": step, "type": "goal", "team": "home",
                "scorer": scorer, "score": f"{curr_score[0]}-{curr_score[1]}"
            })

        if curr_score[1] > last_score[1]:
            shots_a += 1
            scorer_idx = max(0, min(len(away_players) - 1, last_away_touch))
            scorer = away_players[scorer_idx].split('(')[0].strip()
            goal_banner = f"GOAL!  {scorer}  ({match_min}')"
            goal_banner_cd = 30
            last_score = list(curr_score)
            events.append({
                "minute": match_min, "step": step, "type": "goal", "team": "away",
                "scorer": scorer, "score": f"{curr_score[0]}-{curr_score[1]}"
            })

        frame_rgb = env.render()
        import cv2
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        frame_bgr = draw_hud(
            frame=frame_bgr,
            home_team=home_team,
            away_team=away_team,
            home_score=curr_score[0],
            away_score=curr_score[1],
            match_minute=match_min,
            is_second_half=is_second_half,
            home_bgr=home_bgr,
            away_bgr=away_bgr,
            goal_banner=goal_banner if goal_banner_cd > 0 else None,
            raw_obs=raw_o
        )
        if goal_banner_cd > 0:
            goal_banner_cd -= 1

        writer.append_data(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))

    env.close()
    writer.close()

    result = {
        "match_id": str(match_id),
        "requested_render_mode": "3d",
        "render_mode_used": "3d",
        "render_source": "dump",
        "home_team": home_team,
        "away_team": away_team,
        "score": curr_score,
        "events": events,
        "video_url": f"/recordings/{os.path.basename(output_mp4)}",
    }
    print("MATCH_RENDER_RESULT_JSON:" + json.dumps(result))


def render_from_grf_states(payload: Dict[str, Any]):
    """
    Renders 3D broadcast MP4 from recorded .grfstate archive via the Next-Gen ReplayPipeline.
    Uses asynchronous NVENC hardware acceleration and dynamic resolution configuration.
    """
    encoder_type = payload.get("encoder_type", "auto")
    pipeline = ReplayPipeline(encoder_type=encoder_type, queue_size=16)

    res = pipeline.render_match_video(payload)
    match_id = res["match_id"]
    output_mp4 = res["output_mp4"]
    progress_file = payload.get("progress_file")

    video_url = f"/recordings/{os.path.basename(output_mp4)}"
    if progress_file:
        write_progress_atomic(progress_file, {
            "status": "completed", "progress": 100, "step": res["total_frames"],
            "total_steps": res["total_frames"], "match_minute": 90,
            "stage": "3D Broadcast Replay Complete!",
            "video_url": video_url, "completed": True
        })

    result = {
        "match_id": str(match_id),
        "requested_render_mode": "3d",
        "render_mode_used": "3d",
        "render_source": "grf_states",
        "video_url": video_url,
        "render_profile": res["render_profile"]
    }
    print("MATCH_RENDER_RESULT_JSON:" + json.dumps(result))


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 grf_render_worker.py '<payload_json>'", file=sys.stderr)
        sys.exit(1)

    payload_raw = sys.argv[1]
    if os.path.exists(payload_raw):
        with open(payload_raw, "r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = json.loads(payload_raw)

    states_file = payload.get("states_file")
    dump_file = payload.get("dump_file")
    trajectory_file = payload.get("trajectory_file")

    if states_file and os.path.exists(states_file):
        render_from_grf_states(payload)
    elif dump_file and os.path.exists(dump_file):
        render_from_dump(payload)
    elif trajectory_file and os.path.exists(trajectory_file):
        render_from_trajectory_npz(payload)
    else:
        raise ValueError("No valid input file provided (states_file, dump_file, or trajectory_file).")


if __name__ == "__main__":
    main()
