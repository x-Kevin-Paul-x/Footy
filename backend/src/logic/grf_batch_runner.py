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


class GRFBatchRunner:
    def __init__(self):
        self.wsl_python = "/root/venv_baller/bin/python3"
        self.local_ckpt = TIKICK_CHECKPOINT_PATH
        self.local_tikick = LOCAL_TIKICK_DIR
        self.max_steps = FOOTY_GRF_MAX_STEPS
        self.batch_worker_wsl = to_wsl_path(
            BASE_DIR / "backend" / "src" / "logic" / "wsl_workers" / "grf_batch_worker.py"
        )

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
                "home_profiles": fix.get("home_profiles"),
                "away_profiles": fix.get("away_profiles"),
                "home_offensive_bias": fix.get("home_offensive_bias", 50.0),
                "home_defensive_bias": fix.get("home_defensive_bias", 50.0),
                "home_pressing_intensity": fix.get("home_pressing_intensity", 50.0),
                "home_tempo": fix.get("home_tempo", 50.0),
                "away_offensive_bias": fix.get("away_offensive_bias", 50.0),
                "away_defensive_bias": fix.get("away_defensive_bias", 50.0),
                "away_pressing_intensity": fix.get("away_pressing_intensity", 50.0),
                "away_tempo": fix.get("away_tempo", 50.0),
                "home_color": fix.get("home_color") or team_color_from_name(fix.get("home_team", "Home")),
                "away_color": fix.get("away_color") or team_color_from_name(fix.get("away_team", "Away")),
                "trace_npz": to_wsl_path(npz_win),
                "trace_dump": to_wsl_path(dump_win),
                "seed_val": fix.get("seed_val"),
            })

        tikick_wsl = to_wsl_path(self.local_tikick)
        ckpt_wsl = to_wsl_path(self.local_ckpt)

        payload_win = RECORDINGS_DIR / f"batch_payload_{int(time.time()*1000)%100000}.json"

        try:
            payload_win.write_text(json.dumps({
                "fixtures": wsl_fixtures,
                "ckpt_path": ckpt_wsl,
                "tikick_dir": tikick_wsl,
                "max_steps": steps,
            }), encoding="utf-8")

            cmd = [
                "wsl", "-u", "root", self.wsl_python,
                self.batch_worker_wsl, to_wsl_path(payload_win)
            ]

            logger.info("GRF Batch Runner: executing %d fixtures in parallel via batch worker", len(fixtures))
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if "MATCH_BATCH_SIM_RESULT_JSON:" in res.stdout:
                json_str = res.stdout.split("MATCH_BATCH_SIM_RESULT_JSON:")[1].splitlines()[0]
                return json.loads(json_str)

            logger.error("GRF Batch Runner error:\nSTDOUT: %s\nSTDERR: %s", res.stdout, res.stderr)
            raise RuntimeError(f"Batch simulation failed: {res.stderr or res.stdout}")

        finally:
            if payload_win.exists():
                try:
                    payload_win.unlink()
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
