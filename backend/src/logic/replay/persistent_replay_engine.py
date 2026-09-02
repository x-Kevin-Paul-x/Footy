"""
Footy Persistent 3D Broadcast Replay Engine.
Maintains a persistent C++ Google Research Football rendering environment and
Mesa D3D12 NVIDIA OpenGL graphics context across multiple match video renders.
Eliminates repeated ~2.2s environment teardown/recreation overhead in bulk replay pipelines.
"""

import os
import sys
import time
import queue
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import cv2

import gfootball.env as football_env

from logic.grf_trajectory import MatchTrajectory
from logic.grf_state_archive import GRFStateArchiveReader, ReplayIntegrityError
from logic.replay_schema import SIM_STEP_SECONDS
from logic.grf_renderer import (
    team_color_from_name,
    hex_to_bgr,
    draw_pre_match_card,
    draw_studio_stats_card,
    draw_hud
)
from .replay_encoder import create_encoder, ReplayEncoder
from .replay_pipeline import InstrumentedFrameQueue


class PersistentReplayEngine:
    """
    Dedicated persistent replay service holding a singleton C++ GRF OpenGL context.
    Renders sequential match archives with high throughput and zero startup overhead per match.
    """

    def __init__(
        self,
        encoder_type: str = "auto",
        encoder_preset: str = "p4",
        queue_size: int = 16,
        opengl_driver: str = "d3d12_nvidia"
    ):
        self.encoder_type = encoder_type
        self.encoder_preset = encoder_preset
        self.queue_size = queue_size
        self.opengl_driver = opengl_driver

        if opengl_driver == "d3d12_nvidia":
            os.environ["GALLIUM_DRIVER"] = "d3d12"
            os.environ["MESA_D3D12_DEFAULT_ADAPTER_NAME"] = "NVIDIA"
        elif opengl_driver == "llvmpipe":
            os.environ["GALLIUM_DRIVER"] = "llvmpipe"
            os.environ.pop("MESA_D3D12_DEFAULT_ADAPTER_NAME", None)

        self._env: Optional[Any] = None

    def _ensure_env(self):
        """Instantiates persistent C++ GRF environment once."""
        if self._env is None:
            self._env = football_env.create_environment(
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
            self._env.reset()

    def render_match(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Renders a single match using the persistent environment."""
        t_pipeline_start = time.perf_counter()
        self._ensure_env()

        match_id = str(payload.get("match_id", "match"))
        states_file = payload.get("states_file")
        trajectory_file = payload.get("trajectory_file")
        output_mp4 = payload["output_mp4"]
        broadcast_fps = int(payload.get("fps", 10))
        requested_res = str(payload.get("resolution", "720p")).lower()

        if "1080" in requested_res:
            width, height = 1920, 1080
            res_str = "1080p"
        else:
            width, height = 1280, 720
            res_str = "720p"

        if not states_file or not os.path.exists(states_file):
            raise FileNotFoundError(f"State archive not found: {states_file}")

        archive = GRFStateArchiveReader(states_file)
        total_steps = archive.total_steps

        traj = None
        if trajectory_file and os.path.exists(trajectory_file):
            traj = MatchTrajectory.load_from_npz(Path(trajectory_file))
            if total_steps != traj.total_steps:
                archive.close()
                raise ReplayIntegrityError(
                    f"State archive length ({total_steps}) != trajectory steps ({traj.total_steps})"
                )

        archive.validate(
            expected_steps=traj.total_steps if traj else None,
            expected_match_id=match_id if match_id and match_id != "match" else None
        )

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

        half_time_step = total_steps // 2
        if traj:
            for ev in traj.manifest.events:
                if ev.get("type") == "half_time" and "step" in ev:
                    half_time_step = int(ev["step"])
                    break

        encoder = create_encoder(self.encoder_type, preset=self.encoder_preset)
        encoder.start(width=width, height=height, fps=broadcast_fps, output_mp4=output_mp4)
        frame_queue = InstrumentedFrameQueue(maxsize=self.queue_size)

        encoder_exception = None
        t_encoder_write_acc = 0.0

        def _encoder_consumer():
            nonlocal encoder_exception, t_encoder_write_acc
            try:
                while True:
                    frame = frame_queue.get()
                    if frame is None:
                        frame_queue.task_done()
                        break
                    t_w0 = time.perf_counter()
                    encoder.write_frame(frame)
                    t_encoder_write_acc += (time.perf_counter() - t_w0)
                    frame_queue.task_done()
            except Exception as ex:
                encoder_exception = ex

        consumer_thread = threading.Thread(target=_encoder_consumer, daemon=True)
        consumer_thread.start()

        # Profiling accumulators
        t_archive_acc = 0.0
        t_restore_acc = 0.0
        t_render_acc = 0.0
        t_copy_resize_acc = 0.0
        t_hud_acc = 0.0
        t_queue_push_acc = 0.0

        try:
            # 1. Pre-Match Card (3 seconds)
            intro_card_bgr = draw_pre_match_card(
                w=width, h=height, home_team=home_team, away_team=away_team,
                home_players=home_players, away_players=away_players,
                home_formation=home_formation, away_formation=away_formation,
                home_bgr=home_bgr, away_bgr=away_bgr
            )
            intro_card_rgb = cv2.cvtColor(intro_card_bgr, cv2.COLOR_BGR2RGB)
            intro_frames = max(10, int(3.0 * broadcast_fps))
            for _ in range(intro_frames):
                frame_queue.put(intro_card_rgb)

            goal_events_by_step = {}
            if traj:
                for ev in traj.manifest.events:
                    if ev.get("type") == "goal":
                        step_idx = ev.get("step")
                        if step_idx is None:
                            g_min = ev.get("minute", 0)
                            step_idx = int((g_min / 90.0) * total_steps)
                        goal_events_by_step.setdefault(step_idx, []).append(ev)

            goal_banner = None
            goal_banner_cd = 0
            half_time_shown = False
            last_score = [0, 0]
            curr_score = [0, 0]
            shots_h, shots_a = 0, 0
            left_poss, right_poss = 0, 0

            # 2. Sequential Frame Render Loop
            for step in range(total_steps):
                if encoder_exception is not None:
                    raise RuntimeError(f"Encoder thread failed: {encoder_exception}")

                # Archive Read
                t0 = time.perf_counter()
                st_bytes = archive.get_state(step)
                t_archive_acc += (time.perf_counter() - t0)

                # State Restore
                t0 = time.perf_counter()
                self._env.set_state(st_bytes)
                t_restore_acc += (time.perf_counter() - t0)

                # 3D OpenGL Render
                t0 = time.perf_counter()
                frame_rgb = self._env.render(mode='rgb_array')
                t_render_acc += (time.perf_counter() - t0)

                # Frame Sanitization & Resizing
                t0 = time.perf_counter()
                if not isinstance(frame_rgb, np.ndarray) or frame_rgb.dtype != np.uint8:
                    frame_rgb = np.clip(frame_rgb, 0, 255).astype(np.uint8)

                if width != 1280 or height != 720:
                    frame_rgb = cv2.resize(frame_rgb, (width, height), interpolation=cv2.INTER_CUBIC)
                t_copy_resize_acc += (time.perf_counter() - t0)

                # HUD Compositing
                t0 = time.perf_counter()
                raw_o = self._env.observation()[0]
                curr_score = [int(raw_o['score'][0]), int(raw_o['score'][1])]
                b_own = raw_o.get('ball_owned_team', -1)
                if b_own == 0:
                    left_poss += 1
                elif b_own == 1:
                    right_poss += 1

                sim_sec = step * SIM_STEP_SECONDS
                match_min = max(1, min(90, int(sim_sec / 60) + 1))
                is_second_half = step >= half_time_step

                if step in goal_events_by_step:
                    for g_ev in goal_events_by_step[step]:
                        g_team = g_ev.get("team", "home")
                        g_scorer = g_ev.get("player") or g_ev.get("scorer", "Player")
                        g_min = g_ev.get("minute", match_min)
                        team_label = home_team if g_team == "home" else away_team
                        goal_banner = f"GOAL!  {g_scorer} ({team_label})  {g_min}'"
                        goal_banner_cd = int(3.5 * broadcast_fps)

                # Convert RGB to BGR for OpenCV HUD drawing
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

                composite_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                t_hud_acc += (time.perf_counter() - t0)

                # Push to asynchronous bounded queue
                t0 = time.perf_counter()
                frame_queue.put(composite_rgb)
                t_queue_push_acc += (time.perf_counter() - t0)

                # Half-Time Card
                if step == half_time_step and not half_time_shown:
                    half_time_shown = True
                    tot_poss = max(1, left_poss + right_poss)
                    h_pct = round((left_poss / tot_poss) * 100.0, 1)
                    a_pct = round(100.0 - h_pct, 1)
                    ht_card_bgr = draw_studio_stats_card(
                        w=width, h=height, title="HALF TIME",
                        home_team=home_team, away_team=away_team,
                        score=(curr_score[0], curr_score[1]),
                        h_poss=h_pct, a_poss=a_pct,
                        h_shots=shots_h, a_shots=shots_a,
                        home_bgr=home_bgr, away_bgr=away_bgr
                    )
                    ht_card_rgb = cv2.cvtColor(ht_card_bgr, cv2.COLOR_BGR2RGB)
                    for _ in range(int(3.0 * broadcast_fps)):
                        frame_queue.put(ht_card_rgb)

            # 3. Full-Time Card (4 seconds)
            tot_poss = max(1, left_poss + right_poss)
            h_pct = round((left_poss / tot_poss) * 100.0, 1)
            a_pct = round(100.0 - h_pct, 1)
            ft_card_bgr = draw_studio_stats_card(
                w=width, h=height, title="FULL TIME",
                home_team=home_team, away_team=away_team,
                score=(curr_score[0], curr_score[1]),
                h_poss=h_pct, a_poss=a_pct,
                h_shots=shots_h, a_shots=shots_a,
                home_bgr=home_bgr, away_bgr=away_bgr
            )
            ft_card_rgb = cv2.cvtColor(ft_card_bgr, cv2.COLOR_BGR2RGB)
            for _ in range(int(4.0 * broadcast_fps)):
                frame_queue.put(ft_card_rgb)

            # Sentinel to flush encoder
            t_flush_start = time.perf_counter()
            frame_queue.put(None)
            consumer_thread.join()
            encoder.close()
            t_ffmpeg_flush_time = time.perf_counter() - t_flush_start

        finally:
            archive.close()

        total_time = time.perf_counter() - t_pipeline_start
        total_frames = encoder.frames_written
        eff_fps = total_frames / total_time if total_time > 0 else 0.0

        return {
            "match_id": match_id,
            "output_mp4": output_mp4,
            "resolution": res_str,
            "total_frames": total_frames,
            "total_time_sec": round(total_time, 2),
            "effective_fps": round(eff_fps, 1),
            "timing_breakdown_ms": {
                "archive_read_ms": round(t_archive_acc * 1000, 1),
                "state_restore_ms": round(t_restore_acc * 1000, 1),
                "grf_render_ms": round(t_render_acc * 1000, 1),
                "rgb_copy_resize_ms": round(t_copy_resize_acc * 1000, 1),
                "hud_compositing_ms": round(t_hud_acc * 1000, 1),
                "queue_push_block_ms": round(t_queue_push_acc * 1000, 1),
                "encoder_write_ms": round(t_encoder_write_acc * 1000, 1),
                "ffmpeg_flush_ms": round(t_ffmpeg_flush_time * 1000, 1),
            },
            "queue_telemetry": frame_queue.get_telemetry()
        }

    def close(self):
        """Cleans up persistent GRF environment."""
        if self._env is not None:
            self._env.close()
            self._env = None
