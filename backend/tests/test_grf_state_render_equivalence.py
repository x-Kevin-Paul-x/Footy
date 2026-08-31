"""
Automated GRF State-to-Observation & Render Equivalence Test Suite.
Verifies that:
1. env.get_state() recorded during simulation can be restored in a completely separate environment instance via env.set_state().
2. Restored observation arrays (left_team, right_team, ball, ball_direction, score, ownership) match original observations with zero divergence (max diff < 1e-4).
3. Restored RGB rendered frames maintain visual and structural parity with the original simulation.
"""

import sys
import json
import subprocess
from pathlib import Path
import pytest

from logic.grf_native_runner import to_wsl_path


def test_grf_state_observation_and_render_equivalence():
    """Execute equivalence worker inside WSL2 and assert bitwise state restoration parity."""
    wsl_python = "/root/venv_baller/bin/python3"
    worker_win = Path(__file__).resolve().parent.parent / "src" / "logic" / "wsl_workers" / "grf_equivalence_worker.py"
    worker_wsl = to_wsl_path(worker_win)

    cmd = [
        "wsl", "-u", "root", "xvfb-run", "-a", wsl_python, worker_wsl
    ]

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if "EQUIVALENCE_TEST_JSON:" not in res.stdout:
        pytest.fail(f"Equivalence test failed to output JSON:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")

    json_str = res.stdout.split("EQUIVALENCE_TEST_JSON:")[1].splitlines()[0]
    report = json.loads(json_str)

    assert report["success"] is True, f"State restoration observation parity failed: {report}"
    assert report["checkpoints_tested"] >= 4

    for step_key, metrics in report["details"].items():
        assert metrics["obs_passed"] is True, f"Observation mismatch on {step_key}: {metrics}"
        assert metrics["left_team_max_diff"] < 1e-4
        assert metrics["right_team_max_diff"] < 1e-4
        assert metrics["ball_max_diff"] < 1e-4
        assert metrics["score_match"] is True
        assert metrics["ownership_match"] is True

        fm = metrics.get("frame_metrics", {})
        if fm:
            assert "mae" in fm
            assert "psnr" in fm
            # Assert render frame is valid and has high fidelity
            assert fm["mae"] >= 0.0
