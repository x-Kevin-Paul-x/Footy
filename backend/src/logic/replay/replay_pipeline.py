"""
Footy High-Performance Asynchronous Replay Pipeline.
Decouples persistent GRF 3D OpenGL frame rendering from video encoding via
an instrumented bounded frame queue and hardware-accelerated NVENC direct rawvideo pipe.
Supports dynamic resolutions (720p / 1080p), D3D12 NVIDIA hardware acceleration,
and comprehensive telemetry profiling.
"""

import os
import sys
import time
import json
import queue
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import cv2

import gfootball.env as football_env

from logic.grf_trajectory import MatchTrajectory, MatchManifest
from logic.grf_state_archive import GRFStateArchiveReader, ReplayIntegrityError
from logic.replay_schema import SIM_STEP_SECONDS, PerformanceConfig
from logic.grf_renderer import (
    team_color_from_name,
    hex_to_bgr,
    draw_pre_match_card,
    draw_studio_stats_card,
    draw_hud
)
from .replay_encoder import create_encoder, ReplayEncoder


class InstrumentedFrameQueue:
    """
    Thread-safe bounded queue with microsecond-level telemetry tracking
    backpressure, queue depths, producer blocks, and consumer idle durations.
    """

    def __init__(self, maxsize: int = 16):
        self.maxsize = maxsize
        self._q = queue.Queue(maxsize=maxsize)
        self.frames_enqueued = 0
        self.frames_dequeued = 0
        self.producer_block_count = 0
        self.consumer_block_count = 0
        self.total_producer_block_time = 0.0
        self.total_consumer_idle_time = 0.0
        self.depth_samples: List[int] = []
        self._lock = threading.Lock()

    def put(self, item: Any, block: bool = True):
        t0 = time.perf_counter()
        if self._q.full():
            with self._lock:
                self.producer_block_count += 1

        self._q.put(item, block=block)
        t_blocked = time.perf_counter() - t0

        with self._lock:
            self.frames_enqueued += 1
            if t_blocked > 0.0005:
                self.total_producer_block_time += t_blocked
            self.depth_samples.append(self._q.qsize())

    def get(self, block: bool = True) -> Any:
        t0 = time.perf_counter()
        if self._q.empty():
            with self._lock:
                self.consumer_block_count += 1

        item = self._q.get(block=block)
        t_idle = time.perf_counter() - t0

        with self._lock:
            self.frames_dequeued += 1
            if t_idle > 0.0005:
                self.total_consumer_idle_time += t_idle

        return item

    def task_done(self):
        self._q.task_done()

    def get_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            samples = self.depth_samples or [0]
            arr = np.array(samples, dtype=np.float32)
            return {
                "max_capacity": self.maxsize,
                "frames_enqueued": self.frames_enqueued,
                "frames_dequeued": self.frames_dequeued,
                "producer_block_count": self.producer_block_count,
                "consumer_block_count": self.consumer_block_count,
                "time_producer_blocked_ms": round(self.total_producer_block_time * 1000, 2),
                "time_consumer_idle_ms": round(self.total_consumer_idle_time * 1000, 2),
                "max_depth": int(np.max(arr)),
                "mean_depth": round(float(np.mean(arr)), 2),
                "p50_depth": round(float(np.percentile(arr, 50)), 1),
                "p95_depth": round(float(np.percentile(arr, 95)), 1),
            }


class ReplayPipeline:
    """
    Asynchronous 3D TV Broadcast Replay Pipeline.
    Connects GRFStateArchiveReader -> GRF 3D Engine -> InstrumentedFrameQueue -> ReplayEncoder.
    """

    def __init__(
        self,
        encoder_type: str = "auto",
        encoder_preset: str = "p4",
        queue_size: int = 16,
        opengl_driver: str = "auto"
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

    def render_match_video(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        t_pipeline_start = time.perf_counter()

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

        t_setup_start = time.perf_counter()

        # Instantiate persistent C++ GRF environment at native 720p resolution
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

        # Encoder & Instrumented Queue setup
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

        t_startup_time = time.perf_counter() - t_setup_start

        # Profiling accumulators
        profile_enabled = PerformanceConfig.enabled
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
                env.set_state(st_bytes)
                t_restore_acc += (time.perf_counter() - t0)

                # 3D OpenGL Render
                t0 = time.perf_counter()
                frame_rgb = env.render(mode='rgb_array')
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
                raw_o = env.observation()[0]
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

            # Signal sentinel to encoder thread
            t_flush_start = time.perf_counter()
            frame_queue.put(None)
            consumer_thread.join()
            encoder.close()
            t_ffmpeg_flush_time = time.perf_counter() - t_flush_start

        finally:
            archive.close()
            env.close()

        t_shutdown_time = time.perf_counter() - (t_pipeline_start + (time.perf_counter() - t_pipeline_start))
        total_time = time.perf_counter() - t_pipeline_start
        total_frames = encoder.frames_written
        eff_fps = total_frames / total_time if total_time > 0 else 0.0

        queue_telemetry = frame_queue.get_telemetry()

        render_profile = {
            "resolution": res_str,
            "dimensions": f"{width}x{height}",
            "encoder_used": encoder.__class__.__name__,
            "encoder_preset": self.encoder_preset,
            "opengl_driver": self.opengl_driver,
            "total_render_time_ms": round(total_time * 1000, 1),
            "timing_breakdown": {
                "startup_init_ms": round(t_startup_time * 1000, 1),
                "archive_read_ms": round(t_archive_acc * 1000, 1),
                "state_restore_ms": round(t_restore_acc * 1000, 1),
                "grf_render_ms": round(t_render_acc * 1000, 1),
                "rgb_copy_resize_ms": round(t_copy_resize_acc * 1000, 1),
                "hud_compositing_ms": round(t_hud_acc * 1000, 1),
                "queue_push_block_ms": round(t_queue_push_acc * 1000, 1),
                "encoder_write_ms": round(t_encoder_write_acc * 1000, 1),
                "ffmpeg_flush_ms": round(t_ffmpeg_flush_time * 1000, 1),
            },
            "queue_telemetry": queue_telemetry,
            "effective_fps": round(eff_fps, 1),
            "total_frames": total_frames,
            "broadcast_fps": broadcast_fps
        }

        return {
            "match_id": match_id,
            "output_mp4": output_mp4,
            "resolution": res_str,
            "total_frames": total_frames,
            "total_time_sec": round(total_time, 2),
            "effective_fps": round(eff_fps, 1),
            "render_profile": render_profile
        }
