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
import numpy as np
import cv2

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
    draw_studio_stats_card,
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
    # CRITICAL: Preserve original physics_steps_per_frame (10) from replay dump!

    env = football_env.FootballEnv(cfg)
    env.render()
    env.reset()

    os.makedirs(os.path.dirname(output_mp4) or '.', exist_ok=True)
    writer = imageio.get_writer(
        output_mp4, fps=15, codec='libx264',
        pixelformat='yuv420p',
        ffmpeg_params=['-crf', '28', '-preset', 'faster', '-b:v', '220k', '-maxrate', '350k', '-bufsize', '500k']
    )

    intro_card = draw_pre_match_card(
        w=1280, h=720, home_team=home_team, away_team=away_team,
        home_players=home_players, away_players=away_players,
        home_formation=home_formation, away_formation=away_formation,
        home_bgr=home_bgr, away_bgr=away_bgr
    )
    for _ in range(45):
        writer.append_data(intro_card)

    traj = None
    trajectory_file = payload.get("trajectory_file")
    if trajectory_file and os.path.exists(trajectory_file):
        try:
            traj = MatchTrajectory.load_from_npz(Path(trajectory_file))
        except Exception:
            pass

    goal_events_by_step = {}
    if traj:
        for ev in traj.manifest.events:
            if ev.get("type") == "goal":
                s_idx = ev.get("step")
                if s_idx is not None:
                    goal_events_by_step.setdefault(s_idx, []).append(ev)

    curr_score = [0, 0]
    last_score = [0, 0]
    left_poss = 0
    right_poss = 0
    shots_h = 0
    shots_a = 0
    events = traj.manifest.events if traj else []
    goal_banner = None
    goal_banner_cd = 0
    last_home_touch = 10
    last_away_touch = 10

    for step in range(total_steps):
        obs, rew, done, info = env.step([])
        raw_o = obs[0] if isinstance(obs, list) else obs

        # Sync score from trajectory ground-truth if available, otherwise from raw_obs
        if traj and step < len(traj.scores):
            curr_score = [int(traj.scores[step][0]), int(traj.scores[step][1])]
        else:
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

        match_min = max(1, min(90, int((step / max(total_steps, 1)) * 90) + 1))
        is_second_half = step > (total_steps // 2)

        if step in goal_events_by_step:
            for g_ev in goal_events_by_step[step]:
                g_team = g_ev.get("team", "home")
                g_scorer = g_ev.get("player") or g_ev.get("scorer") or (home_players[0] if g_team == "home" else away_players[0])
                g_min = g_ev.get("minute", match_min)
                team_label = home_team if g_team == "home" else away_team
                goal_banner = f"GOAL!  {g_scorer} ({team_label})  {g_min}'"
                goal_banner_cd = 45
            last_score = list(curr_score)
        elif curr_score[0] > last_score[0]:
            shots_h += 1
            scorer_idx = max(0, min(len(home_players) - 1, last_home_touch))
            scorer = home_players[scorer_idx].split('(')[0].strip()
            # If trajectory manifest has goal at this minute, pick that player
            if traj:
                matching_goals = [e for e in traj.manifest.events if e.get("type") == "goal" and e.get("team") == "home" and abs(e.get("minute", 0) - match_min) <= 3]
                if matching_goals:
                    scorer = matching_goals[0].get("player", scorer)
            goal_banner = f"GOAL!  {scorer} ({home_team})  {match_min}'"
            goal_banner_cd = 45
            last_score = list(curr_score)
        elif curr_score[1] > last_score[1]:
            shots_a += 1
            scorer_idx = max(0, min(len(away_players) - 1, last_away_touch))
            scorer = away_players[scorer_idx].split('(')[0].strip()
            if traj:
                matching_goals = [e for e in traj.manifest.events if e.get("type") == "goal" and e.get("team") == "away" and abs(e.get("minute", 0) - match_min) <= 3]
                if matching_goals:
                    scorer = matching_goals[0].get("player", scorer)
            goal_banner = f"GOAL!  {scorer} ({away_team})  {match_min}'"
            goal_banner_cd = 45
            last_score = list(curr_score)

        frame_rgb = env.render(mode="rgb_array")
        if frame_rgb is None or isinstance(frame_rgb, bool):
            continue
        if frame_rgb.dtype != np.uint8:
            if np.issubdtype(frame_rgb.dtype, np.floating) and frame_rgb.max() <= 1.01:
                frame_rgb = (frame_rgb * 255.0).clip(0, 255).astype(np.uint8)
            else:
                frame_rgb = np.clip(frame_rgb, 0, 255).astype(np.uint8)
        import cv2
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        frame_bgr = draw_hud(
            frame=frame_bgr,
            home_team=home_team,
            away_team=away_team,
            score=(curr_score[0], curr_score[1]),
            match_min=match_min,
            home_bgr=home_bgr,
            away_bgr=away_bgr,
            goal_banner=goal_banner if goal_banner_cd > 0 else None,
            is_second_half=is_second_half
        )
        if goal_banner_cd > 0:
            goal_banner_cd -= 1

        writer.append_data(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))

        # Half-Time Studio Recap Card (at step 600)
        if step == (total_steps // 2) and traj:
            ht_card = draw_studio_stats_card(
                w=1280, h=720, title="HALF TIME",
                home_team=home_team, away_team=away_team,
                score=(curr_score[0], curr_score[1]),
                h_poss=traj.manifest.possession[0], a_poss=traj.manifest.possession[1],
                h_shots=traj.manifest.shots[0], a_shots=traj.manifest.shots[1],
                h_sot=traj.manifest.shots_on_target[0], a_sot=traj.manifest.shots_on_target[1],
                h_xg=traj.manifest.xg[0], a_xg=traj.manifest.xg[1],
                home_bgr=home_bgr, away_bgr=away_bgr,
                events=[e for e in traj.manifest.events if e.get("minute", 0) <= 45]
            )
            for _ in range(45):
                writer.append_data(ht_card)

        if progress_file and (step % 30 == 0 or step == total_steps - 1):
            pct = int((step / max(1, total_steps)) * 95)
            write_progress_atomic(progress_file, {
                "status": "rendering", "progress": pct, "step": step,
                "total_steps": total_steps, "match_minute": match_min,
                "stage": f"Replaying 3D Broadcast • {match_min}'/90'...",
                "score": curr_score, "completed": False
            })

    # Full-Time Studio Recap Card at end of match
    if traj:
        ft_card = draw_studio_stats_card(
            w=1280, h=720, title="FULL TIME",
            home_team=home_team, away_team=away_team,
            score=(curr_score[0], curr_score[1]),
            h_poss=traj.manifest.possession[0], a_poss=traj.manifest.possession[1],
            h_shots=traj.manifest.shots[0], a_shots=traj.manifest.shots[1],
            h_sot=traj.manifest.shots_on_target[0], a_sot=traj.manifest.shots_on_target[1],
            h_xg=traj.manifest.xg[0], a_xg=traj.manifest.xg[1],
            home_bgr=home_bgr, away_bgr=away_bgr,
            events=traj.manifest.events,
            motm_player=traj.manifest.events[0].get("player") if traj.manifest.events else None
        )
        for _ in range(60):
            writer.append_data(ft_card)

    env.close()
    writer.close()

    # Space Optimization: clean redundant dump file after 3D video is rendered
    try:
        if dump_file and os.path.exists(dump_file):
            os.remove(dump_file)
        dir_name = os.path.dirname(output_mp4)
        for ext in [".grfstate", "_states.grfstate"]:
            cand = os.path.join(dir_name, f"trace_{match_id}{ext}")
            if os.path.exists(cand):
                os.remove(cand)
    except Exception:
        pass

    if progress_file:
        write_progress_atomic(progress_file, {
            "status": "completed", "progress": 100, "step": total_steps,
            "total_steps": total_steps, "match_minute": 90,
            "stage": "3D Match Replay Complete!",
            "video_url": f"/recordings/{os.path.basename(output_mp4)}",
            "score": curr_score, "completed": True
        })

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

    if dump_file and os.path.exists(dump_file):
        render_from_dump(payload)
    elif states_file and os.path.exists(states_file):
        render_from_grf_states(payload)
    elif trajectory_file and os.path.exists(trajectory_file):
        render_from_trajectory_npz(payload)
    else:
        raise ValueError("No valid input file provided (dump_file, states_file, or trajectory_file).")


if __name__ == "__main__":
    main()
