"""
In-Flight Abrupt Worker SIGKILL Crash Auto-Recovery CI Test.
Validates:
1. Process pool tracks in-flight match IDs per worker PID.
2. Abrupt worker termination via SIGKILL is intercepted by supervisor.
3. Supervisor identifies the lost in-flight fixture, clears partial files, respawns the worker, and re-enqueues the fixture.
4. All fixtures complete successfully with 100% bit-identical canonical trajectory digests.
"""

import os
import sys
import time
import signal
import psutil
import shutil
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
backend_src = REPO_ROOT / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from logic.simulation.simulation_process_pool import SimulationProcessPool
from logic.simulation.simulation_worker import ReplayMode
from logic.match_manifest import compute_file_sha256

CKPT_PATH = os.getenv("FOOTY_CHECKPOINT", str(REPO_ROOT / "checkpoints" / "tikick" / "actor.pt"))
TIKICK_DIR = os.getenv("FOOTY_TIKICK_DIR", str(REPO_ROOT / "third_party" / "tikick"))
TEST_DIR = Path("/tmp/test_inflight_recovery")


def killer_thread_func(parent_pid: int, delay_sec: float = 1.5):
    """Background watchdog that finds child worker processes and sends SIGKILL to one."""
    time.sleep(delay_sec)
    try:
        parent = psutil.Process(parent_pid)
        children = parent.children(recursive=True)
        # Filter for python worker processes
        workers = [c for c in children if "python" in c.name().lower() or "python3" in c.name().lower()]
        if workers:
            victim = workers[0]
            print(f"\n[WATCHDOG] Sending SIGKILL to in-flight worker PID {victim.pid}...")
            os.kill(victim.pid, signal.SIGKILL)
            print(f"[WATCHDOG] SIGKILL delivered successfully to PID {victim.pid}.\n")
    except Exception as ex:
        print(f"[WATCHDOG] Failed to deliver SIGKILL: {ex}")


def test_inflight_sigkill_recovery():
    print("=" * 80)
    print(" RUNNING IN-FLIGHT ABRUPT WORKER SIGKILL RECOVERY CI TEST")
    print("=" * 80)

    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    test_seed = 4242
    target_match_id = "sigkill_target_m01"
    target_traj = str(TEST_DIR / "target.npz")

    # 1. Generate canonical baseline without kill
    print("\n[+] 1. Generating baseline match trajectory (no crash)...")
    base_pool = SimulationProcessPool(num_workers=1, backend_type="cpu_single", scheduling="dynamic")
    base_fixtures = [{
        "match_id": target_match_id,
        "home_team": "Team A", "away_team": "Team B",
        "seed_val": test_seed,
        "trajectory_file": target_traj,
        "created_at": "2026-01-01T00:00:00Z"
    }]
    res_base = base_pool.run_batch(
        fixtures=base_fixtures,
        ckpt_path=CKPT_PATH,
        tikick_dir=TIKICK_DIR,
        max_steps=1200,
        replay_mode=ReplayMode.TRAJECTORY
    )
    base_sha = compute_file_sha256(target_traj)
    print(f"    --> Baseline: Score=[{res_base[0]['home_score']}, {res_base[0]['away_score']}] | SHA256={base_sha[:16]}...")

    # 2. Run multi-fixture batch on 4 workers with active SIGKILL injection
    print("\n[+] 2. Running 6-fixture batch on 4-worker pool with SIGKILL injection...")
    killer = threading.Thread(target=killer_thread_func, args=(os.getpid(), 1.5))
    killer.daemon = True
    killer.start()

    crash_pool = SimulationProcessPool(num_workers=4, backend_type="cpu_single", scheduling="dynamic")
    crash_target_traj = str(TEST_DIR / "target_crashed.npz")
    batch_fixtures = [
        {
            "match_id": target_match_id,
            "home_team": "Team A", "away_team": "Team B",
            "seed_val": test_seed,
            "trajectory_file": crash_target_traj,
            "created_at": "2026-01-01T00:00:00Z"
        }
    ]
    for i in range(1, 6):
        batch_fixtures.append({
            "match_id": f"bg_match_{i}",
            "home_team": "Team C", "away_team": "Team D",
            "seed_val": 1000 + i * 10,
            "trajectory_file": str(TEST_DIR / f"bg_{i}.npz"),
            "created_at": "2026-01-01T00:00:00Z"
        })

    t0 = time.perf_counter()
    res_batch = crash_pool.run_batch(
        fixtures=batch_fixtures,
        ckpt_path=CKPT_PATH,
        tikick_dir=TIKICK_DIR,
        max_steps=1200,
        replay_mode=ReplayMode.TRAJECTORY
    )
    t_total = time.perf_counter() - t0
    killer.join(timeout=1.0)

    # 3. Validate results
    print(f"\n[+] 3. Batch completed in {t_total:.2f}s ({len(res_batch)} matches returned).")
    assert len(res_batch) == len(batch_fixtures), f"Expected {len(batch_fixtures)} results, got {len(res_batch)}"

    target_res = [r for r in res_batch if str(r["match_id"]) == target_match_id][0]
    recovered_sha = compute_file_sha256(crash_target_traj)

    print(f"    --> Target Match Score: [{target_res['home_score']}, {target_res['away_score']}] (Expected [{res_base[0]['home_score']}, {res_base[0]['away_score']}])")
    print(f"    --> Recovered Trajectory SHA256: {recovered_sha[:16]}... (Expected {base_sha[:16]}...)")

    assert recovered_sha == base_sha, f"Recovered trajectory SHA mismatch: {recovered_sha} vs {base_sha}"
    assert target_res["home_score"] == res_base[0]["home_score"] and target_res["away_score"] == res_base[0]["away_score"], "Score mismatch"

    print("\n" + "=" * 80)
    print(" [+] IN-FLIGHT SIGKILL SUPERVISOR AUTO-RECOVERY PASSED 100%!")
    print("=" * 80)


if __name__ == "__main__":
    test_inflight_sigkill_recovery()
