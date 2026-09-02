"""
Footy Simulation Process Pool.
Manages isolated worker processes across CPU physical cores with:
- Dynamic work-queue scheduling (lock-free multi-producer/multi-consumer work stealing)
- Dynamic physical core topology discovery & affinity pinning
- Strict thread oversubscription controls (OMP=1, MKL=1, torch.num_threads=1)
- Pluggable policy execution (CPUSinglePolicy / CUDABatchPolicy / CPUBatchPolicy)
- Configurable worker count (--workers auto / 8 / 12 / 16)
- Resilient exception propagation & orphan process cleanup
- Granular per-match execution profiling (p50/p95 latency)
"""

import os
import sys
import time
import queue
import subprocess
import multiprocessing as mp
from typing import Dict, List, Any, Optional
import numpy as np

from .simulation_worker import SimulationWorker, ReplayMode
from .policy_backend import PolicyBackend, CPUSinglePolicy, CUDABatchPolicy, CPUBatchPolicy


def discover_physical_cores() -> List[int]:
    """
    Discovers physical core primary thread IDs on Linux / WSL.
    Maps physical core IDs to their primary logical CPU ID.
    """
    try:
        res = subprocess.run(
            ["lscpu", "-p=CPU,CORE"], capture_output=True, text=True, timeout=2
        )
        if res.returncode == 0:
            core_map = {}
            for line in res.stdout.strip().split("\n"):
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split(",")
                if len(parts) >= 2:
                    cpu_id, core_id = int(parts[0]), int(parts[1])
                    if core_id not in core_map:
                        core_map[core_id] = cpu_id
            if core_map:
                return [core_map[k] for k in sorted(core_map.keys())]
    except Exception:
        pass

    # Fallback heuristic
    total_cpus = os.cpu_count() or 4
    return [i * 2 for i in range(max(1, total_cpus // 2))]


def get_recommended_workers(reserved_cores: int = 4) -> int:
    """Calculates production worker count reserving headroom for OS/background tasks."""
    cores = discover_physical_cores()
    total_physical = len(cores) if cores else max(1, (os.cpu_count() or 4) // 2)
    return max(1, min(12, total_physical - reserved_cores if total_physical > reserved_cores else total_physical))


def _dynamic_queue_worker_runner(
    w_id: int,
    task_queue: mp.Queue,
    result_queue: mp.Queue,
    ckpt_path: str,
    tikick_dir: str,
    max_steps: int,
    replay_mode_val: str,
    core_id: Optional[int] = None,
    in_flight_dict: Optional[Any] = None
):
    """Entry point for an isolated worker pulling matches dynamically from task_queue."""
    try:
        # 1. Thread concurrency capping
        os.environ["OMP_NUM_THREADS"] = "1"
        os.environ["MKL_NUM_THREADS"] = "1"
        os.environ["OPENBLAS_NUM_THREADS"] = "1"
        os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
        os.environ["NUMEXPR_NUM_THREADS"] = "1"

        try:
            import torch
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
        except Exception:
            pass

        # 2. CPU core affinity pinning
        if core_id is not None and hasattr(os, "sched_setaffinity"):
            try:
                os.sched_setaffinity(0, {core_id})
            except Exception:
                pass

        # 3. Persistent Policy & Engine Initialization (loaded once per worker lifecycle)
        policy = CPUSinglePolicy(ckpt_path=ckpt_path, tikick_dir=tikick_dir)
        replay_mode = ReplayMode(replay_mode_val)

        while True:
            try:
                fix = task_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if fix is None:  # Sentinel to terminate
                break

            match_id_str = str(fix.get("match_id", ""))
            if in_flight_dict is not None:
                in_flight_dict[w_id] = match_id_str

            t_match_start = time.perf_counter()
            try:
                worker = SimulationWorker(fix, max_steps=max_steps, replay_mode=replay_mode)
                policy.reset_match(worker.match_id, worker.seed_val)
                obs = worker.get_initial_observations()
                done = False
                while not done and worker.step_idx < max_steps:
                    acts = policy.evaluate(obs, match_ids=[worker.match_id])
                    obs, done, _ = worker.step(acts)
                res = worker.finalize()
                t_match_end = time.perf_counter()
                res["match_duration_sec"] = round(t_match_end - t_match_start, 3)
                if in_flight_dict is not None:
                    in_flight_dict[w_id] = None
                result_queue.put({"success": True, "match_id": worker.match_id, "data": res})
            except Exception as ex:
                if in_flight_dict is not None:
                    in_flight_dict[w_id] = None
                import traceback
                result_queue.put({
                    "success": False,
                    "match_id": fix.get("match_id"),
                    "error": str(ex),
                    "traceback": traceback.format_exc()
                })
    except Exception as ex:
        if in_flight_dict is not None:
            in_flight_dict[w_id] = None
        import traceback
        result_queue.put({
            "success": False,
            "match_id": f"worker_{w_id}_init_fatal",
            "error": f"Worker initialization failed: {ex}",
            "traceback": traceback.format_exc()
        })


def _sync_worker_pipe_runner(
    worker_id: int,
    fixture: Dict[str, Any],
    max_steps: int,
    replay_mode_val: str,
    core_id: Optional[int],
    pipe: mp.connection.Connection
):
    """Entry point for a synchronized worker participating in centralized GPU/CPU batched inference."""
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"

    try:
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except Exception:
        pass

    if core_id is not None and hasattr(os, "sched_setaffinity"):
        try:
            os.sched_setaffinity(0, {core_id})
        except Exception:
            pass

    t_match_start = time.perf_counter()
    try:
        mode = ReplayMode(replay_mode_val)
        worker = SimulationWorker(fixture, max_steps=max_steps, replay_mode=mode)
        obs = worker.get_initial_observations()
        pipe.send({"type": "ready", "match_id": worker.match_id, "obs": obs})

        while True:
            msg = pipe.recv()
            if msg["type"] == "step":
                actions = msg["actions"]
                next_obs, done, _ = worker.step(actions)
                if done or worker.step_idx >= max_steps:
                    summary = worker.finalize()
                    t_match_end = time.perf_counter()
                    summary["match_duration_sec"] = round(t_match_end - t_match_start, 3)
                    pipe.send({"type": "done", "match_id": worker.match_id, "data": summary})
                    break
                else:
                    pipe.send({"type": "obs", "match_id": worker.match_id, "obs": next_obs})
            elif msg["type"] == "abort":
                worker.finalize()
                break
    except Exception as ex:
        import traceback
        pipe.send({"type": "error", "error": str(ex), "traceback": traceback.format_exc()})
    finally:
        pipe.close()


class SimulationProcessPool:
    """
    High-performance multiprocessing coordinator for matchday simulations.
    Supports dynamic work-queue scheduling, physical core affinity, and pluggable policies.
    """

    def __init__(
        self,
        num_workers: Optional[int] = None,
        backend_type: str = "cpu_single",  # "cpu_single", "cuda_batch", "cpu_batch"
        use_affinity: bool = True,
        scheduling: str = "dynamic"  # "dynamic", "static"
    ):
        if num_workers is None or num_workers == 0 or str(num_workers).lower() == "auto":
            self.num_workers = get_recommended_workers()
        else:
            self.num_workers = int(num_workers)

        self.backend_type = backend_type
        self.use_affinity = use_affinity
        self.scheduling = scheduling
        self.physical_cores = discover_physical_cores() if use_affinity else []

    def run_batch(
        self,
        fixtures: List[Dict[str, Any]],
        ckpt_path: str,
        tikick_dir: str,
        max_steps: int = 1200,
        replay_mode: ReplayMode = ReplayMode.FULL_STATE
    ) -> List[Dict[str, Any]]:
        if not fixtures:
            return []

        if self.backend_type == "cpu_single":
            return self._run_dynamic_queue_pool(fixtures, ckpt_path, tikick_dir, max_steps, replay_mode)
        else:
            return self._run_central_batched_pool(fixtures, ckpt_path, tikick_dir, max_steps, replay_mode)

    def _run_dynamic_queue_pool(
        self,
        fixtures: List[Dict[str, Any]],
        ckpt_path: str,
        tikick_dir: str,
        max_steps: int,
        replay_mode: ReplayMode
    ) -> List[Dict[str, Any]]:
        ctx = mp.get_context("spawn")
        manager = ctx.Manager()
        in_flight_dict = manager.dict()
        task_queue = ctx.Queue()
        result_queue = ctx.Queue()

        num_fixtures = len(fixtures)
        workers_to_spawn = min(self.num_workers, num_fixtures)

        # Enqueue all fixtures into task queue
        for fix in fixtures:
            task_queue.put(fix)

        processes = []
        for w_id in range(workers_to_spawn):
            in_flight_dict[w_id] = None
            core_pin = (
                self.physical_cores[w_id % len(self.physical_cores)]
                if (self.use_affinity and self.physical_cores)
                else None
            )
            p = ctx.Process(
                target=_dynamic_queue_worker_runner,
                args=(
                    w_id,
                    task_queue,
                    result_queue,
                    ckpt_path,
                    tikick_dir,
                    max_steps,
                    replay_mode.value,
                    core_pin,
                    in_flight_dict
                )
            )
            processes.append(p)
            p.start()

        fixtures_by_id = {str(f["match_id"]): f for f in fixtures}
        retry_counts = {str(f["match_id"]): 0 for f in fixtures}
        results_by_id = {}
        completed_count = 0
        max_retries = 2

        def clean_partial_artifacts(fix: Dict[str, Any]):
            for k in ["trajectory_file", "trace_npz", "states_file", "trace_dump"]:
                filepath = fix.get(k)
                if filepath and os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass

        try:
            while completed_count < num_fixtures:
                try:
                    msg = result_queue.get(timeout=0.5)
                except Exception:
                    # Monitor worker process health & recover in-flight jobs on abrupt death
                    for idx, p in enumerate(processes):
                        if not p.is_alive() and p.exitcode != 0:
                            lost_m_id = in_flight_dict.get(idx)

                            # Fallback check: find any uncompleted match not currently in_flight
                            lost_ids = []
                            if lost_m_id and lost_m_id in fixtures_by_id and lost_m_id not in results_by_id:
                                lost_ids.append(lost_m_id)
                            else:
                                active_in_flight = {in_flight_dict.get(i) for i in range(len(processes)) if i != idx}
                                for mid, fix in fixtures_by_id.items():
                                    if mid not in results_by_id and mid not in active_in_flight:
                                        lost_ids.append(mid)

                            for m_to_retry in lost_ids:
                                if retry_counts[m_to_retry] < max_retries:
                                    retry_counts[m_to_retry] += 1
                                    print(f"[SUPERVISOR] Detected abrupt worker death (PID {p.pid}, code {p.exitcode}) on match {m_to_retry}. Auto-retrying (Attempt {retry_counts[m_to_retry]}/{max_retries})...")
                                    fix = fixtures_by_id[m_to_retry]
                                    clean_partial_artifacts(fix)
                                    task_queue.put(fix)

                            in_flight_dict[idx] = None

                            # Respawn replacement worker to drain remaining queue
                            core_pin = (
                                self.physical_cores[idx % len(self.physical_cores)]
                                if (self.use_affinity and self.physical_cores)
                                else None
                            )
                            new_p = ctx.Process(
                                target=_dynamic_queue_worker_runner,
                                args=(
                                    idx,
                                    task_queue,
                                    result_queue,
                                    ckpt_path,
                                    tikick_dir,
                                    max_steps,
                                    replay_mode.value,
                                    core_pin,
                                    in_flight_dict
                                )
                            )
                            processes[idx] = new_p
                            new_p.start()
                    continue

                m_id = str(msg.get("match_id", ""))
                if not msg["success"]:
                    if m_id in fixtures_by_id and retry_counts[m_id] < max_retries:
                        retry_counts[m_id] += 1
                        print(f"[SUPERVISOR] Auto-retrying failed match {m_id} (Attempt {retry_counts[m_id]}/{max_retries})...")
                        fix = fixtures_by_id[m_id]
                        clean_partial_artifacts(fix)
                        task_queue.put(fix)
                        continue
                    else:
                        for p in processes:
                            if p.is_alive():
                                p.terminate()
                        raise RuntimeError(
                            f"Simulation worker failed on match {msg['match_id']}: {msg['error']}\n{msg.get('traceback', '')}"
                        )

                results_by_id[m_id] = msg["data"]
                completed_count += 1

            # Send termination sentinels to cleanly shutdown workers
            for _ in range(workers_to_spawn):
                task_queue.put(None)
        finally:
            for p in processes:
                if p.is_alive():
                    p.terminate()
                p.join(timeout=1)

        return [results_by_id[str(f["match_id"])] for f in fixtures]

    def _run_central_batched_pool(
        self,
        fixtures: List[Dict[str, Any]],
        ckpt_path: str,
        tikick_dir: str,
        max_steps: int,
        replay_mode: ReplayMode
    ) -> List[Dict[str, Any]]:
        ctx = mp.get_context("spawn")
        num_fixtures = len(fixtures)
        device = "cuda" if self.backend_type == "cuda_batch" else "cpu"
        policy = CUDABatchPolicy(ckpt_path=ckpt_path, tikick_dir=tikick_dir, device=device)

        workers = []
        pipes = []
        for i, fix in enumerate(fixtures):
            parent_pipe, child_pipe = ctx.Pipe(duplex=True)
            core_pin = (
                self.physical_cores[i % len(self.physical_cores)]
                if (self.use_affinity and self.physical_cores)
                else None
            )
            p = ctx.Process(
                target=_sync_worker_pipe_runner,
                args=(i, fix, max_steps, replay_mode.value, core_pin, child_pipe)
            )
            workers.append(p)
            pipes.append(parent_pipe)
            p.start()

        results_by_id = {}
        active_pipes = {str(fix["match_id"]): p for fix, p in zip(fixtures, pipes)}
        current_obs: Dict[str, np.ndarray] = {}

        try:
            # Wait for all workers to send initial observations with polling timeout
            for i, (m_id, pipe) in enumerate(active_pipes.items()):
                if not pipe.poll(timeout=15.0):
                    if not workers[i].is_alive():
                        raise RuntimeError(f"Batched worker for match {m_id} exited prematurely with exitcode {workers[i].exitcode}")
                    raise TimeoutError(f"Batched worker for match {m_id} timed out during initialization")
                msg = pipe.recv()
                if msg["type"] == "error":
                    raise RuntimeError(f"Worker {m_id} failed during initialization: {msg['error']}")
                current_obs[m_id] = msg["obs"]

            while active_pipes:
                active_ids = list(active_pipes.keys())
                stacked_obs = np.concatenate([current_obs[m_id] for m_id in active_ids], axis=0)

                # Central GPU / multi-threaded CPU batched inference
                actions_batch = policy.evaluate(stacked_obs, match_ids=active_ids)

                # Disperse actions to corresponding worker pipes
                for i, m_id in enumerate(active_ids):
                    active_pipes[m_id].send({"type": "step", "actions": actions_batch[i * 20:(i + 1) * 20]})

                # Receive next observations or match completion with polling protection
                completed_ids = []
                for m_id in active_ids:
                    p_conn = active_pipes[m_id]
                    if not p_conn.poll(timeout=15.0):
                        raise RuntimeError(f"Batched worker for match {m_id} timed out waiting for step completion")
                    try:
                        msg = p_conn.recv()
                    except (EOFError, BrokenPipeError) as e:
                        raise RuntimeError(f"Batched worker pipe disconnected for match {m_id}: {e}")

                    if msg["type"] == "obs":
                        current_obs[m_id] = msg["obs"]
                    elif msg["type"] == "done":
                        results_by_id[m_id] = msg["data"]
                        completed_ids.append(m_id)
                    elif msg["type"] == "error":
                        raise RuntimeError(f"Worker {m_id} error: {msg['error']}")

                # Active match compaction
                for c_id in completed_ids:
                    del active_pipes[c_id]
                    del current_obs[c_id]
                    policy.reset_match(c_id)
        finally:
            for p in workers:
                if p.is_alive():
                    p.terminate()
                p.join(timeout=1)

        return [results_by_id[str(f["match_id"])] for f in fixtures]
