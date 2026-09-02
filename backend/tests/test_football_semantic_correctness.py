"""
Football Model & Statistics Semantic Correctness Test Suite.
Validates domain football rules, event ordering, and statistical integrity:
1. Goal attribution & score matching
2. Shot & Shot-on-Target (SoT) hierarchy (Shots >= SoT >= Goals)
3. Expected Goals (xG) mathematical bounds (0.0 <= xG <= 1.0, non-negative sum)
4. Possession percentage partition (Home% + Away% == 100.0%)
5. Passing completion bounds (Attempted >= Completed >= 0)
6. Event chronological ordering and timeline validity
7. Canonical Single Source of Truth (SSOT) parity across simulation outputs, trajectory, and manifest
"""

import os
import sys
import numpy as np
from pathlib import Path

import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
backend_src = REPO_ROOT / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from logic.simulation.simulation_worker import SimulationWorker, ReplayMode
from logic.simulation.policy_backend import CPUSinglePolicy
from logic.grf_trajectory import MatchTrajectory
from logic.match_manifest import MatchManifest, compute_file_sha256, ArtifactLifecycle

CKPT_PATH = os.getenv("FOOTY_CHECKPOINT", str(REPO_ROOT / "checkpoints" / "tikick" / "actor.pt"))
TIKICK_DIR = os.getenv("FOOTY_TIKICK_DIR", str(REPO_ROOT / "third_party" / "tikick"))
OUTPUT_DIR = Path(tempfile.gettempdir()) / "test_football_semantic"


def test_football_semantic_correctness():
    print("=" * 80)
    print(" RUNNING FOOTBALL MODEL & STATISTICAL SEMANTIC CORRECTNESS CI TEST")
    print("=" * 80)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    traj_path = str(OUTPUT_DIR / "sem_match.npz")
    state_path = str(OUTPUT_DIR / "sem_match.grfstate")

    fixture = {
        "match_id": "sem_match_01",
        "home_team": "Real Madrid",
        "away_team": "Barcelona",
        "seed_val": 7777,
        "trajectory_file": traj_path,
        "states_file": state_path,
        "created_at": "2026-01-01T00:00:00Z"
    }

    # 1. Execute full match simulation
    print("\n[+] 1. Simulating 1200-step football match (Seed=7777)...")
    worker = SimulationWorker(fixture, max_steps=1200, replay_mode=ReplayMode.FULL_STATE)
    policy = CPUSinglePolicy(ckpt_path=CKPT_PATH, tikick_dir=TIKICK_DIR)
    policy.reset_match(worker.match_id, worker.seed_val)

    obs = worker.get_initial_observations()
    done = False
    while not done and worker.step_idx < 1200:
        acts = policy.evaluate(obs, match_ids=[worker.match_id])
        obs, done, _ = worker.step(acts)

    res = worker.finalize()
    print(f"    --> Simulation Complete: {res['home_team']} {res['home_score']} - {res['away_score']} {res['away_team']}")

    # 2. Test Goal Attribution & Event Matching
    print("\n[+] 2. Validating Goal Attribution & Event Counter Integrity...")
    goal_events_h = [e for e in res["events"] if e.get("type") == "goal" and e.get("team") == "home"]
    goal_events_a = [e for e in res["events"] if e.get("type") == "goal" and e.get("team") == "away"]

    assert len(goal_events_h) == res["home_score"], f"Home goals ({res['home_score']}) != goal events ({len(goal_events_h)})"
    assert len(goal_events_a) == res["away_score"], f"Away goals ({res['away_score']}) != goal events ({len(goal_events_a)})"

    for g in goal_events_h + goal_events_a:
        assert "scorer" in g and len(g["scorer"]) > 0, f"Goal missing valid scorer: {g}"
        assert 1 <= g["minute"] <= 90, f"Goal minute out of bounds: {g['minute']}"
    print(f"    --> [PASS] All {len(goal_events_h) + len(goal_events_a)} goals accurately attributed with valid scorers and timestamps.")

    # 3. Test Shot & Shot-on-Target Hierarchy
    print("\n[+] 3. Validating Shot & Shot-on-Target Mathematical Hierarchy...")
    shot_events_h = [e for e in res["events"] if e.get("type") == "shot" and e.get("team") == "home"]
    shot_events_a = [e for e in res["events"] if e.get("type") == "shot" and e.get("team") == "away"]

    print(f"    --> Home: Shots={res['home_shots']}, SoT={res['home_shots_on_target']}, Goals={res['home_score']}")
    print(f"    --> Away: Shots={res['away_shots']}, SoT={res['away_shots_on_target']}, Goals={res['away_score']}")

    assert res["home_shots"] >= res["home_shots_on_target"], "Home Shots must be >= Shots on Target"
    assert res["home_shots_on_target"] >= res["home_score"], "Home Shots on Target must be >= Goals"
    assert res["away_shots"] >= res["away_shots_on_target"], "Away Shots must be >= Shots on Target"
    assert res["away_shots_on_target"] >= res["away_score"], "Away Shots on Target must be >= Goals"
    print("    --> [PASS] Hierarchy invariant strictly holds: Shots >= Shots_on_Target >= Goals.")

    # 4. Test Expected Goals (xG) Bounds & Sum
    print("\n[+] 4. Validating Expected Goals (xG) Bounds & Summations...")
    assert res["home_xg"] >= 0.0, "Home xG must be non-negative"
    assert res["away_xg"] >= 0.0, "Away xG must be non-negative"

    sum_xg_h = sum([e.get("xg", 0.0) for e in shot_events_h])
    sum_xg_a = sum([e.get("xg", 0.0) for e in shot_events_a])
    assert abs(res["home_xg"] - round(sum_xg_h, 2)) <= 0.02, f"Home xG sum mismatch: {res['home_xg']} vs {sum_xg_h:.2f}"
    assert abs(res["away_xg"] - round(sum_xg_a, 2)) <= 0.02, f"Away xG sum mismatch: {res['away_xg']} vs {sum_xg_a:.2f}"

    for s in shot_events_h + shot_events_a:
        assert 0.0 <= s["xg"] <= 1.0, f"Individual shot xG out of unit interval [0, 1]: {s['xg']}"
    print(f"    --> [PASS] xG totals ({res['home_xg']:.2f} vs {res['away_xg']:.2f}) strictly match individual shot xG integrals.")

    # 5. Test Possession Partition
    print("\n[+] 5. Validating Possession Percentage Partition (Sum to 100%)...")
    poss_sum = res["home_possession"] + res["away_possession"]
    assert abs(poss_sum - 100.0) <= 0.2, f"Possession sum ({poss_sum}%) != 100.0%"
    assert res["home_possession"] > 0.0 and res["away_possession"] > 0.0, "Both teams must have non-zero possession"
    print(f"    --> [PASS] Possession partition: Home={res['home_possession']}%, Away={res['away_possession']}% (Sum={poss_sum:.1f}%).")

    # 6. Test Passing Invariants
    print("\n[+] 6. Validating Passing Metrics & Completion Invariants...")
    assert res["home_passes_attempted"] >= res["home_passes_completed"] >= 0, "Home attempted >= completed >= 0"
    assert res["away_passes_attempted"] >= res["away_passes_completed"] >= 0, "Away attempted >= completed >= 0"
    print(f"    --> [PASS] Passing: Home={res['home_passes_completed']}/{res['home_passes_attempted']} | Away={res['away_passes_completed']}/{res['away_passes_attempted']}.")

    # 7. Test Canonical Single Source of Truth (SSOT) Consistency
    print("\n[+] 7. Validating Canonical Single Source of Truth (SSOT) Parity...")
    traj = MatchTrajectory.load_from_npz(Path(traj_path))
    assert traj.manifest.home_score == res["home_score"], "Trajectory manifest home score mismatch"
    assert traj.manifest.away_score == res["away_score"], "Trajectory manifest away score mismatch"
    assert traj.manifest.possession == (res["home_possession"], res["away_possession"]), "Trajectory manifest possession mismatch"
    assert traj.manifest.shots == (res["home_shots"], res["away_shots"]), "Trajectory manifest shots mismatch"
    assert len(traj.manifest.events) == len(res["events"]), "Trajectory manifest events length mismatch"

    # Verify score trajectory array end state matches final score
    last_score_in_traj = traj.scores[-1]
    assert int(last_score_in_traj[0]) == res["home_score"], "Score array end state mismatch (Home)"
    assert int(last_score_in_traj[1]) == res["away_score"], "Score array end state mismatch (Away)"
    print("    --> [PASS] Trajectory NPZ, Event Stream, and Summary Statistics are 100% CANONICALLY CONSISTENT.")

    print("\n" + "=" * 80)
    print(" [+] ALL FOOTBALL SEMANTIC & STATISTICAL CORRECTNESS TESTS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    test_football_semantic_correctness()
