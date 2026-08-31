"""
Native Google Research Football (GRF) 3D Simulation & Replay Bridge.
Executes authentic 11v11 MARL physics matches with Dual TiKick Actor Policies via WSL2.
Supports decoupled high-throughput pure simulation (1-3s) and standalone 3D TV broadcast video rendering.
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

from config import (
    RECORDINGS_DIR,
    TIKICK_CHECKPOINT_PATH,
    LOCAL_TIKICK_DIR,
    FOOTY_GRF_MAX_STEPS,
    BASE_DIR
)
from logic.grf_renderer import team_color_from_name, hex_to_bgr

logger = logging.getLogger(__name__)


def to_wsl_path(win_path: Path) -> str:
    """Convert Windows Path to WSL /mnt/... mount path."""
    resolved = win_path.resolve()
    drive = resolved.drive.replace(":", "").lower()
    rest = str(resolved.relative_to(resolved.anchor)).replace("\\", "/")
    return f"/mnt/{drive}/{rest}"


class GRFNativeRunner:
    """
    Windows-to-WSL2 Bridge for GRF match simulation and broadcast video rendering.
    """

    def __init__(self):
        self.wsl_python = "/root/venv_baller/bin/python3"
        self.local_ckpt = TIKICK_CHECKPOINT_PATH
        self.local_tikick = LOCAL_TIKICK_DIR
        self.max_steps = FOOTY_GRF_MAX_STEPS
        self.sim_worker_wsl = to_wsl_path(BASE_DIR / "logic" / "wsl_workers" / "grf_sim_worker.py")
        self.render_worker_wsl = to_wsl_path(BASE_DIR / "logic" / "wsl_workers" / "grf_render_worker.py")

    _cached_available = None
    _last_check_time = 0.0

    def is_available(self, force_recheck: bool = False) -> bool:
        """Check if WSL2 Python environment and GRF bindings are available."""
        now = time.time()
        if not force_recheck and GRFNativeRunner._cached_available is not None and (now - GRFNativeRunner._last_check_time) < 60.0:
            return GRFNativeRunner._cached_available
        try:
            res = subprocess.run(
                ["wsl", "-u", "root", self.wsl_python, "-c",
                 "import gfootball, torch; print('OK')"],
                capture_output=True, text=True, timeout=20
            )
            GRFNativeRunner._cached_available = "OK" in res.stdout
            GRFNativeRunner._last_check_time = now
            return GRFNativeRunner._cached_available
        except Exception:
            GRFNativeRunner._cached_available = False
            GRFNativeRunner._last_check_time = now
            return False

    def simulate(
        self,
        home_team: Any,
        away_team: Any,
        max_steps: Optional[int] = None,
        home_players: Optional[List[str]] = None,
        away_players: Optional[List[str]] = None,
        home_formation: str = "4-3-3",
        away_formation: str = "4-2-3-1",
        home_color: Optional[str] = None,
        away_color: Optional[str] = None,
        match_id: Optional[str] = None,
        seed_val: Optional[int] = None,
        render_video: bool = False,
        record_grf_states: Optional[bool] = None,
        record_dump: bool = False,
        render_mode: str = "auto",
        home_tactics: Optional[Any] = None,
        away_tactics: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute pure 11v11 MARL match simulation (Phase A).
        Fast, zero-rendering. Records .npz trajectory and optionally .grfstate / .dump.
        """
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        h_name = getattr(home_team, "name", str(home_team))
        a_name = getattr(away_team, "name", str(away_team))
        m_id = str(match_id or f"match_{int(time.time()*1000)%100000}")
        steps = max_steps or self.max_steps

        _home_color = home_color or team_color_from_name(h_name)
        _away_color = away_color or team_color_from_name(a_name)

        trace_npz_win = RECORDINGS_DIR / f"trace_{m_id}.npz"
        trace_dump_win = RECORDINGS_DIR / f"trace_{m_id}.dump"
        trace_grfstate_win = RECORDINGS_DIR / f"trace_{m_id}.grfstate"

        # Build tactics and player profiles from Footy domain objects
        from logic.footy_grf_adapter import FootyGRFAdapter
        h_tac = home_tactics or FootyGRFAdapter.build_team_tactics(home_team, formation=home_formation)
        a_tac = away_tactics or FootyGRFAdapter.build_team_tactics(away_team, formation=away_formation)

        if record_grf_states is None:
            should_record_states = bool(render_video and render_mode != "2d")
        else:
            should_record_states = bool(record_grf_states)

        payload = {
            "match_id": m_id,
            "home_team": h_name,
            "away_team": a_name,
            "home_formation": home_formation or h_tac.formation,
            "away_formation": away_formation or a_tac.formation,
            "home_players": home_players or [p.name for p in h_tac.roster],
            "away_players": away_players or [p.name for p in a_tac.roster],
            "home_profiles": [p.to_dict() for p in h_tac.roster],
            "away_profiles": [p.to_dict() for p in a_tac.roster],
            "home_offensive_bias": h_tac.offensive_bias,
            "home_defensive_bias": h_tac.defensive_bias,
            "home_pressing_intensity": h_tac.pressing_intensity,
            "home_tempo": h_tac.tempo,
            "away_offensive_bias": a_tac.offensive_bias,
            "away_defensive_bias": a_tac.defensive_bias,
            "away_pressing_intensity": a_tac.pressing_intensity,
            "away_tempo": a_tac.tempo,
            "home_color": _home_color,
            "away_color": _away_color,
            "max_steps": steps,
            "ckpt_path": to_wsl_path(self.local_ckpt),
            "tikick_dir": to_wsl_path(self.local_tikick),
            "trace_npz": to_wsl_path(trace_npz_win),
            "trace_dump": to_wsl_path(trace_dump_win) if record_dump else None,
            "states_file": to_wsl_path(trace_grfstate_win) if should_record_states else None,
            "record_grf_states": should_record_states,
            "record_dump": bool(record_dump),
            "seed_val": seed_val,
        }

        # 1. Try communicating with persistent daemon if active (fastest)
        sim_res = self._try_daemon_simulate(payload)
        if sim_res is None:
            # 2. Fall back to one-shot worker command
            cmd = [
                "wsl", "-u", "root", self.wsl_python,
                self.sim_worker_wsl, json.dumps(payload)
            ]
            logger.info("GRF Simulator: running one-shot simulation for match=%s", m_id)
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if "MATCH_SIM_RESULT_JSON:" in res.stdout:
                json_str = res.stdout.split("MATCH_SIM_RESULT_JSON:")[1].splitlines()[0]
                sim_res = json.loads(json_str)
            else:
                logger.error("GRF Simulator error:\nSTDOUT: %s\nSTDERR: %s", res.stdout, res.stderr)
                raise RuntimeError(f"GRF simulation execution failed: {res.stderr or res.stdout}")

        if render_video:
            render_out = self.render_replay(
                match_id=m_id,
                home_team=h_name,
                away_team=a_name,
                trajectory_file=str(trace_npz_win),
                home_players=home_players,
                away_players=away_players,
                home_formation=home_formation,
                away_formation=away_formation,
                home_color=_home_color,
                away_color=_away_color,
                mode=render_mode,
            )
            sim_res["video_url"] = render_out.get("video_url", f"/recordings/match_{m_id}.mp4")
            sim_res["render_mode_used"] = render_out.get("render_mode_used", render_mode)

        return sim_res

    def _try_daemon_simulate(self, payload: Dict[str, Any], port: int = 58210) -> Optional[Dict[str, Any]]:
        """Attempt sending simulation payload to persistent daemon over local socket."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect(("127.0.0.1", port))
                s.settimeout(60.0)
                req_bytes = json.dumps(payload).encode('utf-8') + b"\n"
                s.sendall(req_bytes)

                resp_bytes = b""
                while True:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    resp_bytes += chunk
                    if b"\n" in resp_bytes:
                        break

                if resp_bytes.strip():
                    return json.loads(resp_bytes.decode('utf-8').strip())
        except Exception:
            return None
        return None

    def render_replay(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        trajectory_file: Optional[str] = None,
        dump_file: Optional[str] = None,
        states_file: Optional[str] = None,
        home_players: Optional[List[str]] = None,
        away_players: Optional[List[str]] = None,
        home_formation: str = "4-3-3",
        away_formation: str = "4-2-3-1",
        home_color: Optional[str] = None,
        away_color: Optional[str] = None,
        output_mp4: Optional[str] = None,
        mode: str = "3d",
    ) -> Dict[str, Any]:
        """
        Execute standalone TV broadcast video rendering from recorded trace (Phase B).
        Supports mode='3d' (authentic photorealistic 3D GRF engine), mode='2d' (fast tactical radar),
        and mode='auto' (resilient fallback hierarchy).
        """
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        m_id = str(match_id)
        out_win = Path(output_mp4) if output_mp4 else (RECORDINGS_DIR / f"match_{m_id}.mp4")
        traj_win = Path(trajectory_file) if trajectory_file else (RECORDINGS_DIR / f"trace_{m_id}.npz")
        dump_win = Path(dump_file) if dump_file else (RECORDINGS_DIR / f"trace_{m_id}.dump")
        prog_win = RECORDINGS_DIR / f"progress_{m_id}.json"

        # Resolve candidate states file
        states_win = None
        if states_file and Path(states_file).exists():
            states_win = Path(states_file)
        else:
            for ext in [".grfstate", "_states.grfstate", "_states.pkl"]:
                candidate = Path(str(traj_win).replace(".npz", ext))
                if candidate.exists():
                    states_win = candidate
                    break

        # 2D Tactical Replay Mode
        if mode == "2d":
            if not traj_win.exists():
                raise FileNotFoundError(f"2D replay requested (mode='2d'), but trajectory file not found: {traj_win}")
            from logic.grf_trajectory import MatchTrajectory
            from logic.grf_renderer import render_video_from_trajectory
            logger.info("GRF Renderer: rendering 2D tactical broadcast for match=%s", m_id)

            def _progress_cb(pct: int, step: int, total_steps: int, match_min: int):
                try:
                    tmp_p = prog_win.with_suffix(".json.tmp")
                    with open(tmp_p, "w", encoding="utf-8") as pf:
                        json.dump({
                            "status": "rendering", "progress": pct, "step": step,
                            "total_steps": total_steps, "match_minute": match_min,
                            "stage": f"Replaying 2D Broadcast • {match_min}'/90'...",
                            "completed": False
                        }, pf)
                    os.replace(tmp_p, prog_win)
                except Exception:
                    pass

            traj = MatchTrajectory.load_from_npz(traj_win)
            video_url = render_video_from_trajectory(traj, str(out_win), progress_callback=_progress_cb)

            try:
                with open(prog_win, "w", encoding="utf-8") as pf:
                    json.dump({
                        "status": "completed", "progress": 100, "step": traj.total_steps,
                        "total_steps": traj.total_steps, "match_minute": 90,
                        "stage": "2D Match Replay Complete!",
                        "video_url": video_url, "score": list(traj.manifest.score), "completed": True
                    }, pf)
            except Exception:
                pass

            return {
                "match_id": str(m_id),
                "render_mode_used": "2d",
                "home_team": traj.manifest.home_team,
                "away_team": traj.manifest.away_team,
                "score": list(traj.manifest.score),
                "possession": list(traj.manifest.possession),
                "shots": list(traj.manifest.shots),
                "events": traj.manifest.events,
                "video_url": video_url,
            }

        # 3D Mode Check: Fail fast if explicit 3D mode was requested without valid 3D sources
        has_3d_source = (states_win is not None and states_win.exists()) or dump_win.exists()
        if mode == "3d" and not has_3d_source:
            raise RuntimeError(
                f"Explicit 3D replay requested (mode='3d'), but neither GRF state archive "
                f"({states_win or 'trace_' + m_id + '.grfstate'}) nor native dump ({dump_win}) was found. "
                f"To allow graceful fallback to 2D tactical replay, specify mode='auto'."
            )

        # Fallback to 2D if in auto mode and no 3D source is present
        if mode == "auto" and not has_3d_source and traj_win.exists():
            return self.render_replay(
                match_id=match_id, home_team=home_team, away_team=away_team,
                trajectory_file=str(traj_win), home_players=home_players,
                away_players=away_players, home_formation=home_formation,
                away_formation=away_formation, home_color=home_color,
                away_color=away_color, output_mp4=output_mp4, mode="2d"
            )

        _home_color = home_color or team_color_from_name(home_team)
        _away_color = away_color or team_color_from_name(away_team)

        payload = {
            "match_id": m_id,
            "mode": mode,
            "home_team": home_team,
            "away_team": away_team,
            "states_file": to_wsl_path(states_win) if states_win else None,
            "trajectory_file": to_wsl_path(traj_win) if traj_win.exists() else None,
            "dump_file": to_wsl_path(dump_win) if dump_win.exists() else None,
            "output_mp4": to_wsl_path(out_win),
            "progress_file": to_wsl_path(prog_win),
            "home_players": home_players,
            "away_players": away_players,
            "home_formation": home_formation,
            "away_formation": away_formation,
            "home_color": _home_color,
            "away_color": _away_color,
        }

        cmd = [
            "wsl", "-u", "root", "bash", "-c",
            f'xvfb-run -a -s "-screen 0 1280x720x24" {self.wsl_python} {self.render_worker_wsl} \'{json.dumps(payload)}\''
        ]

        logger.info("GRF Renderer: rendering authentic 3D broadcast via WSL worker for match=%s", m_id)
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if "MATCH_RENDER_RESULT_JSON:" in res.stdout:
            json_str = res.stdout.split("MATCH_RENDER_RESULT_JSON:")[1].splitlines()[0]
            return json.loads(json_str)

        logger.error("GRF Renderer error:\nSTDOUT: %s\nSTDERR: %s", res.stdout, res.stderr)
        raise RuntimeError(f"GRF video render failed: {res.stderr or res.stdout}")

    def run_match(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        render_video: bool = False,
        max_steps: Optional[int] = None,
        home_players: Optional[List[str]] = None,
        away_players: Optional[List[str]] = None,
        home_formation: str = "4-3-3",
        away_formation: str = "4-2-3-1",
        home_color: Optional[str] = None,
        away_color: Optional[str] = None,
        trace_file: Optional[str] = None,
        seed_val: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Unified entry point: if trajectory .npz exists and render_video=True, renders replay directly.
        Otherwise simulates match and optionally renders video.
        """
        traj_candidate = RECORDINGS_DIR / f"trace_{match_id}.npz"
        if render_video and traj_candidate.exists():
            logger.info("Existing trajectory .npz found for %s; rendering replay from trajectory.", match_id)
            return self.render_replay(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                trajectory_file=str(traj_candidate),
                home_players=home_players,
                away_players=away_players,
                home_formation=home_formation,
                away_formation=away_formation,
                home_color=home_color,
                away_color=away_color,
            )

        return self.simulate(
            home_team=home_team,
            away_team=away_team,
            max_steps=max_steps,
            home_players=home_players,
            away_players=away_players,
            home_formation=home_formation,
            away_formation=away_formation,
            home_color=home_color,
            away_color=away_color,
            match_id=match_id,
            seed_val=seed_val,
            render_video=render_video,
        )
