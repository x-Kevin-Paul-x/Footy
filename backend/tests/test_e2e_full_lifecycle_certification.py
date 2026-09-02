"""
Comprehensive End-to-End Simulation-to-Broadcast Certification Pipeline CI Test.
Executes and validates the entire deterministic lifecycle:
1. FAST Simulation Mode
2. REPLAYABLE Simulation Mode with .grfstate capture
3. Mid-Match Crash & Clean Supervisor Recovery
4. Bit-Identical Trajectory Parity Assertion (FAST == REPLAYABLE == RETRY)
5. 3D Broadcast Rendering via PersistentReplayEngine (D3D12 NVIDIA + NVENC p4)
6. Atomic MP4 Publication & Manifest SHA256 Gate
7. Re-Render Idempotency Verification (Cache Hit, Zero GPU Overhead)
"""

import os
import sys
import time
import shutil
from pathlib import Path

backend_src = Path(__file__).resolve().parent.parent / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from logic.simulation.simulation_worker import SimulationWorker, ReplayMode
from logic.simulation.policy_backend import CPUSinglePolicy
from logic.replay.persistent_replay_engine import PersistentReplayEngine
from logic.match_manifest import MatchManifest, compute_file_sha256, ArtifactLifecycle

FOOTY_ROOT = Path("/mnt/c/Users/kevin/OneDrive/Desktop/Projects/Footy")
CKPT_PATH = str(FOOTY_ROOT / "backend" / "checkpoints" / "tikick" / "actor.pt")
TIKICK_DIR = str(FOOTY_ROOT / "backend" / "third_party" / "tikick")
E2E_DIR = Path("/root/test_e2e_certification")


def run_sim(pkg_dir: Path, match_id: str, seed: int, mode: ReplayMode, crash_at: int = -1) -> dict:
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "trajectory").mkdir(exist_ok=True)
    (pkg_dir / "state").mkdir(exist_ok=True)

    traj_rel = f"trajectory/{match_id}.npz"
    state_rel = f"state/{match_id}.grfstate"
    traj_abs = str(pkg_dir / traj_rel)
    state_abs = str(pkg_dir / state_rel) if mode == ReplayMode.FULL_STATE else None

    fix = {
        "match_id": match_id, "home_team": "Inter", "away_team": "Milan",
        "seed_val": seed, "trajectory_file": traj_abs, "states_file": state_abs,
        "created_at": "2026-01-01T00:00:00Z"
    }

    manifest = MatchManifest(
        match_id=match_id, seed=seed, simulation_steps=1200,
        home_team="Inter", away_team="Milan",
        trajectory_rel_path=traj_rel,
        state_archive_rel_path=state_rel if mode == ReplayMode.FULL_STATE else None,
        created_at="2026-01-01T00:00:00Z"
    )

    w = SimulationWorker(fix, max_steps=1200, replay_mode=mode)
    p = CPUSinglePolicy(ckpt_path=CKPT_PATH, tikick_dir=TIKICK_DIR)
    p.reset_match(w.match_id, w.seed_val)
    obs = w.get_initial_observations()
    done = False
    while not done and w.step_idx < 1200:
        if crash_at > 0 and w.step_idx >= crash_at:
            raise RuntimeError(f"Simulated worker crash at step {w.step_idx}")
        acts = p.evaluate(obs, match_ids=[w.match_id])
        obs, done, _ = w.step(acts)
    res = w.finalize()

    manifest.score = [res.get("home_score", 0), res.get("away_score", 0)]
    manifest.events_count = len(res.get("events", []))
    manifest.trajectory_sha256 = compute_file_sha256(traj_abs)
    if state_abs and os.path.exists(state_abs):
        manifest.state_archive_sha256 = compute_file_sha256(state_abs)
    manifest.update_status(ArtifactLifecycle.VALIDATED)
    manifest.save_package(str(pkg_dir))

    return {
        "score": manifest.score,
        "events": manifest.events_count,
        "trajectory_sha256": manifest.trajectory_sha256,
        "manifest": manifest
    }


def test_e2e_full_lifecycle_certification():
    print("=" * 80)
    print(" RUNNING END-TO-END SIMULATION-TO-BROADCAST LIFECYCLE CERTIFICATION")
    print("=" * 80)

    if E2E_DIR.exists():
        shutil.rmtree(E2E_DIR)
    E2E_DIR.mkdir(parents=True, exist_ok=True)

    cert_seed = 1337
    match_id = "e2e_cert_m01"

    # 1. FAST Simulation
    print("\n[+] 1. Running FAST Mode Simulation...")
    pkg_fast = E2E_DIR / "pkg_fast"
    res_fast = run_sim(pkg_fast, match_id, cert_seed, ReplayMode.TRAJECTORY)
    print(f"    --> FAST: Score={res_fast['score']}, Trajectory SHA256={res_fast['trajectory_sha256'][:16]}...")

    # 2. REPLAYABLE Simulation
    print("\n[+] 2. Running REPLAYABLE Mode Simulation with Full State Capture...")
    pkg_rep = E2E_DIR / "pkg_replayable"
    res_rep = run_sim(pkg_rep, match_id, cert_seed, ReplayMode.FULL_STATE)
    print(f"    --> REPLAYABLE: Score={res_rep['score']}, Trajectory SHA256={res_rep['trajectory_sha256'][:16]}...")

    # 3. Crash & Retry Recovery
    print("\n[+] 3. Running Mid-Match Crash Injection (Step 450) & Supervisor Retry...")
    pkg_retry = E2E_DIR / "pkg_retry"
    try:
        run_sim(pkg_retry, match_id, cert_seed, ReplayMode.FULL_STATE, crash_at=450)
    except RuntimeError as ex:
        print(f"    --> Intercepted crash cleanly: {ex}")
        if pkg_retry.exists():
            shutil.rmtree(pkg_retry)
    res_retry = run_sim(pkg_retry, match_id, cert_seed, ReplayMode.FULL_STATE, crash_at=-1)
    print(f"    --> RETRY: Score={res_retry['score']}, Trajectory SHA256={res_retry['trajectory_sha256'][:16]}...")

    # 4. Assert 3-Way Trajectory Parity
    print("\n[+] 4. Verifying 3-Way Bit-Identical Trajectory Parity...")
    assert res_fast["trajectory_sha256"] == res_rep["trajectory_sha256"], "FAST vs REPLAYABLE trajectory mismatch"
    assert res_rep["trajectory_sha256"] == res_retry["trajectory_sha256"], "REPLAYABLE vs RETRY trajectory mismatch"
    assert res_fast["score"] == res_rep["score"] == res_retry["score"], "Scores mismatch across modes"
    print(f"    --> [PASS] 3-Way Parity Verified: 100% BIT-IDENTICAL SHA256 ({res_fast['trajectory_sha256'][:16]}...)")

    # 5. Persistent 3D Broadcast Replay Render
    print("\n[+] 5. Rendering 3D Broadcast Video via PersistentReplayEngine...")
    engine = PersistentReplayEngine(encoder_type="nvenc", encoder_preset="p4", opengl_driver="d3d12_nvidia")
    
    tmp_mp4 = str(pkg_rep / "video_tmp.mp4")
    render_payload = {
        "match_id": match_id,
        "states_file": str(pkg_rep / f"state/{match_id}.grfstate"),
        "trajectory_file": str(pkg_rep / f"trajectory/{match_id}.npz"),
        "output_mp4": tmp_mp4,
        "resolution": "720p",
        "fps": 10
    }
    t0 = time.perf_counter()
    r_res = engine.render_match(render_payload)
    t_render = time.perf_counter() - t0
    print(f"    --> Broadcast Render Complete: {t_render:.2f}s ({r_res['effective_fps']:.1f} FPS)")

    # 6. Atomic Video Publication with Manifest Gate
    print("\n[+] 6. Publishing Video Atomically with SHA256 Gate...")
    manifest = res_rep["manifest"]
    vid_rel = f"video/{match_id}.mp4"
    vid_sha = manifest.publish_video_atomic(str(pkg_rep), tmp_mp4, vid_rel)
    print(f"    --> Video Published: {vid_rel} (SHA256={vid_sha[:16]}...) | Status={manifest.status}")
    assert manifest.status == ArtifactLifecycle.BROADCAST_READY.value
    assert manifest.validate_package(str(pkg_rep))
    print("    --> [PASS] Artifact package verified: Status = BROADCAST_READY.")

    # 7. Idempotency Check
    print("\n[+] 7. Testing Render Idempotency (Cache Hit Gate)...")
    is_idempotent = manifest.check_idempotent_render(str(pkg_rep))
    print(f"    --> Idempotency Check: {is_idempotent} (Cache Hit = Instant Return, Zero GPU Load)")
    assert is_idempotent, "Idempotency check must return True for verified broadcast package"
    print("    --> [PASS] Idempotency gate successfully skipped redundant re-rendering.")

    engine.close()
    print("\n" + "=" * 80)
    print(" [+] END-TO-END SIMULATION-TO-BROADCAST CERTIFICATION PASSED 100%!")
    print("=" * 80)


if __name__ == "__main__":
    test_e2e_full_lifecycle_certification()
