"""
Multi-Seed Topology Invariance Matrix CI Test Suite.
Evaluates 6 diverse match seeds across multiple worker topologies (1W, 8W, 12W, 16W).
Proves that topology invariance is universal across seeds.
"""

import os
import sys
import shutil
from pathlib import Path

backend_src = Path(__file__).resolve().parent.parent / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from logic.simulation.simulation_process_pool import SimulationProcessPool
from logic.simulation.simulation_worker import SimulationWorker, ReplayMode
from logic.simulation.policy_backend import CPUSinglePolicy
from logic.match_manifest import compute_file_sha256

FOOTY_ROOT = Path("/mnt/c/Users/kevin/OneDrive/Desktop/Projects/Footy")
CKPT_PATH = str(FOOTY_ROOT / "backend" / "checkpoints" / "tikick" / "actor.pt")
TIKICK_DIR = str(FOOTY_ROOT / "backend" / "third_party" / "tikick")
MATRIX_DIR = Path("/root/test_multi_seed_matrix")


def test_multi_seed_topology_invariance():
    print("=" * 85)
    print(" RUNNING MULTI-SEED TOPOLOGY INVARIANCE MATRIX CI TEST")
    print("=" * 85)

    if MATRIX_DIR.exists():
        shutil.rmtree(MATRIX_DIR)
    MATRIX_DIR.mkdir(parents=True, exist_ok=True)

    test_seeds = [42, 1337, 4242, 7777, 9999, 12345]
    topologies = [8, 12, 16]

    print(f"\n[+] Testing {len(test_seeds)} Distinct Seeds across 1W Baseline and Dynamic Pools ({topologies})...")

    matrix_results = {}

    for s_idx, seed in enumerate(test_seeds, start=1):
        print(f"\n--- Seed {s_idx}/{len(test_seeds)}: {seed} ---")
        
        # 1. Single Worker Isolated Baseline
        base_traj = str(MATRIX_DIR / f"seed_{seed}_1w.npz")
        fix_base = {
            "match_id": f"matrix_s{seed}",
            "home_team": "Team A",
            "away_team": "Team B",
            "seed_val": seed,
            "trajectory_file": base_traj,
            "created_at": "2026-01-01T00:00:00Z"
        }
        w = SimulationWorker(fix_base, max_steps=1200, replay_mode=ReplayMode.TRAJECTORY)
        p = CPUSinglePolicy(ckpt_path=CKPT_PATH, tikick_dir=TIKICK_DIR)
        p.reset_match(w.match_id, w.seed_val)
        obs = w.get_initial_observations()
        done = False
        while not done and w.step_idx < 1200:
            acts = p.evaluate(obs, match_ids=[w.match_id])
            obs, done, _ = w.step(acts)
        res_base = w.finalize()
        base_sha = compute_file_sha256(base_traj)
        
        print(f"  --> 1W Baseline:   Score=[{res_base['home_score']}, {res_base['away_score']}] | Events={len(res_base['events'])} | SHA256={base_sha[:16]}...")

        matrix_results[seed] = {
            "score": [res_base["home_score"], res_base["away_score"]],
            "events": len(res_base["events"]),
            "1w_sha": base_sha,
            "pool_shas": {}
        }

        # 2. Dynamic Pool Topologies
        for num_w in topologies:
            pool_traj = str(MATRIX_DIR / f"seed_{seed}_{num_w}w.npz")
            fix_pool = [{
                "match_id": f"matrix_s{seed}",
                "home_team": "Team A",
                "away_team": "Team B",
                "seed_val": seed,
                "trajectory_file": pool_traj,
                "created_at": "2026-01-01T00:00:00Z"
            }]

            pool = SimulationProcessPool(num_workers=num_w, backend_type="cpu_single", scheduling="dynamic")
            res_pool = pool.run_batch(
                fixtures=fix_pool,
                ckpt_path=CKPT_PATH,
                tikick_dir=TIKICK_DIR,
                max_steps=1200,
                replay_mode=ReplayMode.TRAJECTORY
            )
            pool_sha = compute_file_sha256(pool_traj)
            matrix_results[seed]["pool_shas"][num_w] = pool_sha

            print(f"  --> Pool ({num_w:2d}W):     Score=[{res_pool[0]['home_score']}, {res_pool[0]['away_score']}] | SHA256={pool_sha[:16]}... [{'PASS' if pool_sha == base_sha else 'FAIL'}]")
            assert pool_sha == base_sha, f"Topology {num_w}W diverged from 1W baseline on seed {seed}!"

    print("\n" + "=" * 85)
    print(" MULTI-SEED TOPOLOGY INVARIANCE MATRIX SUMMARY:")
    print(f" {'Seed':<8} | {'Score':<8} | {'Events':<7} | {'1W SHA256':<18} | {'8W Parity':<10} | {'12W Parity':<11} | {'16W Parity':<10}")
    print("-" * 85)
    for seed, data in matrix_results.items():
        s_str = f"[{data['score'][0]}-{data['score'][1]}]"
        print(f" {seed:<8} | {s_str:<8} | {data['events']:<7} | {data['1w_sha'][:16]}.. | {'MATCH (100%)':<10} | {'MATCH (100%)':<11} | {'MATCH (100%)':<10}")
    print("=" * 85)
    print(" [+] ALL 6 SEEDS PROVEN 100% INVARIANT ACROSS ALL POOL TOPOLOGIES!")
    print("=" * 85)


if __name__ == "__main__":
    test_multi_seed_topology_invariance()
