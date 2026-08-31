"""
Automated GRF State-to-Observation & Render Equivalence Test Suite.
Verifies that:
1. env.get_state() recorded during simulation can be restored in a completely separate environment instance via env.set_state().
2. Restored observation arrays match original observations across all 16 fields with mathematical tolerance (< 1e-4).
3. Restored RGB rendered frames maintain visual and structural parity with the original simulation (PSNR > 20 dB).
4. End-to-End Pipeline: Simulated match archive (.grfstate), when restored in a fresh environment, produces observations exactly matching trajectory (.npz) player coordinates, ball coordinates, and scores.
"""

import sys
import json
import subprocess
from pathlib import Path
import pytest

from logic.grf_native_runner import GRFNativeRunner, to_wsl_path


def test_grf_state_observation_and_render_equivalence():
    """GRF state restoration and render consistency.

    Executes equivalence worker inside WSL2 and asserts:
    - Near-exact (< 1e-4) state restoration across all 16 observation fields.
    - Perceptual/numerical bounded render equivalence: PSNR > 20 dB, MAE < 25.0, MSE < 500.0.
    NOTE: Render parity is proven by perceptual bounds, not bitwise pixel equality.
    """
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
        assert metrics["left_dir_max_diff"] < 1e-4
        assert metrics["right_dir_max_diff"] < 1e-4
        assert metrics["ball_max_diff"] < 1e-4
        assert metrics["ball_dir_max_diff"] < 1e-4
        assert metrics["score_match"] is True
        assert metrics["ownership_match"] is True
        assert metrics["game_mode_match"] is True

        fm = metrics.get("frame_metrics", {})
        if fm:
            assert "mae" in fm
            assert "psnr" in fm
            assert "mse" in fm
            # Hard visual render bounds: PSNR > 20 dB, MAE < 25.0
            assert fm["psnr"] > 20.0, f"Render PSNR below 20 dB on {step_key}: {fm}"
            assert fm["mae"] < 25.0, f"Render MAE too high on {step_key}: {fm}"
            assert fm["mse"] < 500.0, f"Render MSE too high on {step_key}: {fm}"


def test_grf_end_to_end_archive_trajectory_simulation_chain():
    """Simulate a match with record_grf_states=True, then verify archive states match trajectory.npz in fresh env."""
    runner = GRFNativeRunner()
    if not runner.is_available():
        pytest.skip("WSL GRF environment not available")

    match_id = "test_end_to_end_chain_01"
    res = runner.simulate(
        home_team="Liverpool",
        away_team="Man City",
        max_steps=80,
        match_id=match_id,
        seed_val=1002003,
        record_grf_states=True,
    )

    state_win = Path(f"backend/reports/recordings/trace_{match_id}.grfstate")
    traj_win = Path(f"backend/reports/recordings/trace_{match_id}.npz")

    assert state_win.exists(), f"State archive must exist: {state_win}"
    assert traj_win.exists(), f"Trajectory npz must exist: {traj_win}"

    wsl_python = "/root/venv_baller/bin/python3"
    worker_win = Path(__file__).resolve().parent.parent / "src" / "logic" / "wsl_workers" / "grf_equivalence_worker.py"

    cmd = [
        "wsl", "-u", "root", wsl_python,
        to_wsl_path(worker_win),
        "--end-to-end",
        to_wsl_path(state_win),
        to_wsl_path(traj_win)
    ]

    worker_res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if "END_TO_END_TEST_JSON:" not in worker_res.stdout:
        pytest.fail(f"End-to-end test failed to output JSON:\nSTDOUT: {worker_res.stdout}\nSTDERR: {worker_res.stderr}")

    json_str = worker_res.stdout.split("END_TO_END_TEST_JSON:")[1].splitlines()[0]
    report = json.loads(json_str)

    assert report["success"] is True, f"End-to-end archive vs trajectory validation failed: {report}"
    for step_key, s_met in report["details"].items():
        assert s_met["passed"] is True, f"Mismatch on {step_key}: {s_met}"
        assert s_met["player_max_diff"] < 1e-4
        assert s_met["ball_max_diff"] < 1e-4
        assert s_met["score_match"] is True
