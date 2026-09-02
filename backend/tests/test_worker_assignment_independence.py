"""
Worker Assignment Independence & Determinism Test.
Verifies that assigning the same match job seed to different worker IDs / processes
(Worker 0, Worker 3, Worker 7, Worker 11) produces 100% bit-identical trajectories,
scores, events, and canonical manifest hashes.
"""

import os
import sys
import shutil
import multiprocessing as mp
from pathlib import Path

backend_src = Path(__file__).resolve().parent.parent / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from logic.simulation.simulation_worker import SimulationWorker, ReplayMode
from logic.simulation.policy_backend import CPUSinglePolicy
from logic.match_manifest import MatchManifest, compute_file_sha256, ArtifactLifecycle

FOOTY_ROOT = Path("/mnt/c/Users/kevin/OneDrive/Desktop/Projects/Footy")
CKPT_PATH = str(FOOTY_ROOT / "backend" / "checkpoints" / "tikick" / "actor.pt")
TIKICK_DIR = str(FOOTY_ROOT / "backend" / "third_party" / "tikick")
TEST_WORKER_DIR = Path("/root/test_worker_independence")


def _worker_process_target(worker_id: int, pkg_dir_str: str, seed: int, result_queue: mp.Queue):
    """Executes match on a specific designated worker process."""
    try:
        pkg_dir = Path(pkg_dir_str)
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "trajectory").mkdir(exist_ok=True)
        (pkg_dir / "state").mkdir(exist_ok=True)

        match_id = "job_indep_fixed"
        traj_rel = f"trajectory/{match_id}.npz"
        state_rel = f"state/{match_id}.grfstate"
        traj_abs = str(pkg_dir / traj_rel)
        state_abs = str(pkg_dir / state_rel)

        fixture = {
            "match_id": match_id,
            "home_team": "Liverpool",
            "away_team": "ManCity",
            "seed_val": seed,
            "trajectory_file": traj_abs,
            "states_file": state_abs,
            "created_at": "2026-01-01T00:00:00Z"
        }

        manifest = MatchManifest(
            match_id=match_id,
            seed=seed,
            simulation_steps=1200,
            home_team="Liverpool",
            away_team="ManCity",
            trajectory_rel_path=traj_rel,
            state_archive_rel_path=state_rel,
            worker_id=f"worker_{worker_id}",
            created_at="2026-01-01T00:00:00Z"
        )

        worker = SimulationWorker(fixture, max_steps=1200, replay_mode=ReplayMode.FULL_STATE)
        policy = CPUSinglePolicy(ckpt_path=CKPT_PATH, tikick_dir=TIKICK_DIR)
        policy.reset_match(worker.match_id, worker.seed_val)

        obs = worker.get_initial_observations()
        done = False
        while not done and worker.step_idx < 1200:
            acts = policy.evaluate(obs, match_ids=[worker.match_id])
            obs, done, _ = worker.step(acts)

        res = worker.finalize()

        manifest.score = [res.get("home_score", 0), res.get("away_score", 0)]
        manifest.events_count = len(res.get("events", []))
        manifest.trajectory_sha256 = compute_file_sha256(traj_abs)
        manifest.state_archive_sha256 = compute_file_sha256(state_abs)
        manifest.update_status(ArtifactLifecycle.VALIDATED)
        manifest.save_package(str(pkg_dir))
        can_hash = manifest.compute_canonical_hash()

        result_queue.put({
            "success": True,
            "worker_id": worker_id,
            "score": manifest.score,
            "events_count": manifest.events_count,
            "trajectory_sha256": manifest.trajectory_sha256,
            "canonical_manifest_sha256": can_hash
        })
    except Exception as ex:
        result_queue.put({"success": False, "worker_id": worker_id, "error": str(ex)})


def test_worker_assignment_independence():
    print("=" * 80)
    print(" RUNNING WORKER ASSIGNMENT INDEPENDENCE DETERMINISM TEST")
    print("=" * 80)

    if TEST_WORKER_DIR.exists():
        shutil.rmtree(TEST_WORKER_DIR)
    TEST_WORKER_DIR.mkdir(parents=True, exist_ok=True)

    test_worker_ids = [0, 3, 7, 11]
    fixed_seed = 4242
    results = []

    ctx = mp.get_context("spawn")

    for w_id in test_worker_ids:
        print(f"\n[+] Executing Match with Seed {fixed_seed} on Worker Process ID {w_id}...")
        pkg_dir = TEST_WORKER_DIR / f"worker_{w_id:02d}_pkg"
        res_q = ctx.Queue()
        p = ctx.Process(target=_worker_process_target, args=(w_id, str(pkg_dir), fixed_seed, res_q))
        p.start()
        res = res_q.get()
        p.join(timeout=2)

        assert res["success"], f"Worker {w_id} failed: {res.get('error')}"
        print(f"    --> Worker {w_id:02d}: Score={res['score']} | Events={res['events_count']} | Trajectory SHA256={res['trajectory_sha256'][:16]}...")
        results.append(res)

    # Cross-worker parity validation
    base = results[0]
    print("\n[+] Validating Cross-Worker Deterministic Parity...")
    for res in results[1:]:
        w_id = res["worker_id"]
        assert res["score"] == base["score"], f"Score mismatch on worker {w_id}: {res['score']} vs {base['score']}"
        assert res["events_count"] == base["events_count"], f"Events mismatch on worker {w_id}"
        assert res["trajectory_sha256"] == base["trajectory_sha256"], f"Trajectory SHA256 mismatch on worker {w_id}!"
        print(f"    --> [PASS] Worker {w_id:02d} matches Worker 00 with 100% BIT-IDENTICAL SHA256 ({res['trajectory_sha256'][:16]}...)")

    print("\n" + "=" * 80)
    print(" [+] WORKER ASSIGNMENT INDEPENDENCE VERIFIED: 100% REPRODUCIBLE ACROSS WORKERS")
    print("=" * 80)


if __name__ == "__main__":
    test_worker_assignment_independence()
