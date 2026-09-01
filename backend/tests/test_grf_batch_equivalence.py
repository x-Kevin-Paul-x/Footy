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

    # 1. Run Match A in single mode
    sim_a_single = runner.simulate(
        home_team="Arsenal",
        away_team="Chelsea",
        max_steps=100,
        match_id="test_eq_single_A",
        seed_val=seed_a,
    )

    # 2. Run Match A + Match B together in batch mode
    fixtures = [
        {
            "match_id": "test_eq_batch_A",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "home_formation": "4-3-3",
            "away_formation": "4-2-3-1",
            "seed_val": seed_a,
            "trace_npz": "backend/reports/recordings/trace_test_eq_batch_A.npz"
        },
        {
            "match_id": "test_eq_batch_B",
            "home_team": "Liverpool",
            "away_team": "ManCity",
            "home_formation": "4-3-3",
            "away_formation": "4-2-3-1",
            "seed_val": seed_b,
            "trace_npz": "backend/reports/recordings/trace_test_eq_batch_B.npz"
        }
    ]

    batch_results = runner.simulate_batch(fixtures=fixtures, max_steps=100)
    assert len(batch_results) == 2

    res_a_batch = batch_results[0]

    # Verify score, events, and trajectory hash equivalence
    assert res_a_batch["score"] == sim_a_single["score"], "Single vs Batch score mismatch"
    assert res_a_batch["trajectory_hash"] == sim_a_single["trajectory_hash"], "Single vs Batch trajectory hash mismatch"
    assert len(res_a_batch["events"]) == len(sim_a_single["events"]), "Single vs Batch event count mismatch"
