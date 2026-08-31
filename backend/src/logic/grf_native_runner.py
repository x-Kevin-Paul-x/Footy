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
    ) -> Dict[str, Any]:
        """
        Execute pure 11v11 MARL match simulation (Phase A).
        Fast, zero-rendering. Records .npz trajectory and .dump trace.
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

        payload = {
            "match_id": m_id,
            "home_team": h_name,
            "away_team": a_name,
            "home_formation": home_formation,
            "away_formation": away_formation,
            "home_players": home_players,
            "away_players": away_players,
            "home_color": _home_color,
            "away_color": _away_color,
            "max_steps": steps,
            "ckpt_path": to_wsl_path(self.local_ckpt),
            "tikick_dir": to_wsl_path(self.local_tikick),
            "trace_npz": to_wsl_path(trace_npz_win),
            "trace_dump": to_wsl_path(trace_dump_win),
            "seed_val": seed_val,
        }

        cmd = [
            "wsl", "-u", "root", self.wsl_python,
            self.sim_worker_wsl, json.dumps(payload)
        ]

        logger.info("GRF Simulator: running match simulation for match=%s", m_id)
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if "MATCH_SIM_RESULT_JSON:" in res.stdout:
            json_str = res.stdout.split("MATCH_SIM_RESULT_JSON:")[1].splitlines()[0]
            result = json.loads(json_str)

            # If video requested immediately, render replay
            if render_video:
                self.render_replay(
                    match_id=m_id,
                    home_team=h_name,
                    away_team=a_name,
                    dump_file=str(trace_dump_win),
                    home_players=home_players,
                    away_players=away_players,
                    home_formation=home_formation,
                    away_formation=away_formation,
                    home_color=_home_color,
                    away_color=_away_color,
                )
                result["video_url"] = f"/recordings/match_{m_id}.mp4"

            return result

        logger.error("GRF Simulator error:\nSTDOUT: %s\nSTDERR: %s", res.stdout, res.stderr)
        raise RuntimeError(f"GRF simulation execution failed: {res.stderr or res.stdout}")

    def render_replay(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        dump_file: Optional[str] = None,
        home_players: Optional[List[str]] = None,
        away_players: Optional[List[str]] = None,
        home_formation: str = "4-3-3",
        away_formation: str = "4-2-3-1",
        home_color: Optional[str] = None,
        away_color: Optional[str] = None,
        output_mp4: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute standalone 3D TV broadcast video rendering from recorded trace (Phase B).
        """
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        m_id = str(match_id)
        out_win = Path(output_mp4) if output_mp4 else (RECORDINGS_DIR / f"match_{m_id}.mp4")
        dump_win = Path(dump_file) if dump_file else (RECORDINGS_DIR / f"trace_{m_id}.dump")
        prog_win = RECORDINGS_DIR / f"progress_{m_id}.json"

        if not dump_win.exists():
            raise FileNotFoundError(f"Trace dump file not found for match replay: {dump_win}")

        _home_color = home_color or team_color_from_name(home_team)
        _away_color = away_color or team_color_from_name(away_team)

        payload = {
            "match_id": m_id,
            "home_team": home_team,
            "away_team": away_team,
            "dump_file": to_wsl_path(dump_win),
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

        logger.info("GRF Renderer: rendering 3D broadcast video for match=%s", m_id)
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
        Unified entry point: if trace exists and render_video=True, renders replay directly.
        Otherwise simulates match and optionally renders video.
        """
        trace_candidate = trace_file or str(RECORDINGS_DIR / f"trace_{match_id}.dump")
        if render_video and os.path.exists(trace_candidate):
            logger.info("Existing trace found for %s; rendering replay from trace.", match_id)
            return self.render_replay(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                dump_file=trace_candidate,
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
