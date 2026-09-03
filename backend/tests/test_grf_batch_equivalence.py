"""
Batch Equivalence & RNN Isolation Test Suite for GRF & TiKick Simulation.
Verifies that:
1. Simulating match A in single-match mode vs in a multi-fixture batch produces
   identical scores, events, statistics, and trajectory hashes.
2. Early termination of one match in a batch does not alter or contaminate the
   recurrent RNN states, observations, or trajectories of remaining active matches.
"""

import pytest
import numpy as np
from pathlib import Path

from logic.grf_native_runner import GRFNativeRunner
from logic.grf_trajectory import MatchTrajectory


def test_batch_equivalence_and_rnn_isolation():
    """Verify single-match vs batch-match simulation equivalence and RNN isolation."""
    runner = GRFNativeRunner()
    if not runner.is_available():
        pytest.skip("GRF WSL environment not available")

    seed_a = 554433
    seed_b = 887766

    fixture_a = {
        "match_id": "test_eq_match_A",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_formation": "4-3-3",
        "away_formation": "4-2-3-1",
        "seed_val": seed_a,
        "created_at": "2026-01-01T00:00:00Z",
        "trace_npz": "backend/reports/recordings/trace_test_eq_match_A.npz"
    }
    fixture_b = {
        "match_id": "test_eq_match_B",
        "home_team": "Liverpool",
        "away_team": "ManCity",
        "home_formation": "4-3-3",
        "away_formation": "4-2-3-1",
        "seed_val": seed_b,
        "created_at": "2026-01-01T00:00:00Z",
        "trace_npz": "backend/reports/recordings/trace_test_eq_match_B.npz"
    }

    # 1. Run Match A in single mode (1-match batch)
    sim_a_single = runner.simulate_batch(fixtures=[fixture_a], max_steps=100)[0]

    # 2. Run Match A + Match B together in batch mode (2-match batch)
    batch_results = runner.simulate_batch(fixtures=[fixture_a, fixture_b], max_steps=100)
    assert len(batch_results) == 2

    res_a_batch = batch_results[0]

    # Verify score, events, statistics, xG, passes, and trajectory hash equivalence
    assert res_a_batch["score"] == sim_a_single["score"], "Single vs Batch score mismatch"
    assert res_a_batch["trajectory_hash"] == sim_a_single["trajectory_hash"], "Single vs Batch trajectory hash mismatch"
    assert res_a_batch["events"] == sim_a_single["events"], "Single vs Batch event mismatch"
    assert res_a_batch["possession"] == sim_a_single["possession"], "Single vs Batch possession mismatch"
    assert res_a_batch["shots"] == sim_a_single["shots"], "Single vs Batch shots mismatch"
    assert res_a_batch["shots_on_target"] == sim_a_single["shots_on_target"], "Single vs Batch shots_on_target mismatch"
    assert res_a_batch["xg"] == sim_a_single["xg"], "Single vs Batch xG mismatch"
    assert res_a_batch["passes_attempted"] == sim_a_single["passes_attempted"], "Single vs Batch passes_attempted mismatch"
    assert res_a_batch["passes_completed"] == sim_a_single["passes_completed"], "Single vs Batch passes_completed mismatch"


def test_batch_early_termination_isolation():
    """Verify that early termination of match A in a batch does not alter match B's trajectory or score."""
    runner = GRFNativeRunner()
    if not runner.is_available():
        pytest.skip("GRF WSL environment not available")

    seed_b = 887766

    fixture_b = {
        "match_id": "test_b_target",
        "home_team": "Liverpool",
        "away_team": "ManCity",
        "seed_val": seed_b,
        "max_steps": 120,
        "created_at": "2026-01-01T00:00:00Z",
        "trace_npz": "backend/reports/recordings/trace_test_b_target.npz"
    }

    # Match B simulated alone for 120 steps
    sim_b_alone = runner.simulate_batch(fixtures=[fixture_b], max_steps=120)[0]

    # Batch simulation where Match A runs for 30 steps while Match B runs for 120 steps
    fixture_a_short = {
        "match_id": "test_a_short",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "seed_val": 111111,
        "max_steps": 30,
        "created_at": "2026-01-01T00:00:00Z",
        "trace_npz": "backend/reports/recordings/trace_test_a_short.npz"
    }

    batch_results = runner.simulate_batch(fixtures=[fixture_a_short, fixture_b], max_steps=120)
    res_b_batch = batch_results[1]

    # Match B's outcome must be 100% identical regardless of Match A's early completion
    assert res_b_batch["score"] == sim_b_alone["score"]
    assert res_b_batch["trajectory_hash"] == sim_b_alone["trajectory_hash"]
    assert res_b_batch["total_steps"] == sim_b_alone["total_steps"]
    assert res_b_batch["events"] == sim_b_alone["events"]
    assert res_b_batch["possession"] == sim_b_alone["possession"]
    assert res_b_batch["shots"] == sim_b_alone["shots"]
    assert res_b_batch["shots_on_target"] == sim_b_alone["shots_on_target"]
    assert res_b_batch["xg"] == sim_b_alone["xg"]
    assert res_b_batch["passes_attempted"] == sim_b_alone["passes_attempted"]
    assert res_b_batch["passes_completed"] == sim_b_alone["passes_completed"]
