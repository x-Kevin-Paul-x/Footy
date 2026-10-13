"""
Benchmark Harness and Performance Measurement Engine for Footy.
Measures:
- Worker scalability (1, 2, 4, 8, 12 workers)
- Fixture throughput and step throughput (steps/sec)
- Latency distributions (p50, p95, min, max, spread)
- Correctness hashing (guaranteeing determinism across iterations)
- Machine and dependency environment manifest
- Isolated workspace directories (never touches production data/ or recordings/)
"""

import os
import sys
import time
import json
import hashlib
import platform
import statistics
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple


def get_machine_metadata() -> Dict[str, Any]:
    """Collect hardware and runtime environment metadata."""
    meta: Dict[str, Any] = {
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "cpu_count_logical": os.cpu_count() or 1,
    }

    try:
        import psutil  # type: ignore
        vm = psutil.virtual_memory()
        meta["total_ram_gb"] = round(vm.total / (1024 ** 3), 2)
        meta["available_ram_gb"] = round(vm.available / (1024 ** 3), 2)
    except ImportError:
        meta["total_ram_gb"] = "psutil_not_installed"

    try:
        import torch  # type: ignore
        meta["torch_version"] = torch.__version__
        meta["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            meta["cuda_device_name"] = torch.cuda.get_device_name(0)
            meta["cuda_device_count"] = torch.cuda.device_count()
    except ImportError:
        meta["torch_version"] = "torch_not_installed"
        meta["cuda_available"] = False

    return meta


@dataclass
class BenchmarkConfig:
    """Benchmark execution matrix configuration."""
    worker_counts: List[int] = field(default_factory=lambda: [1, 2, 4])
    fixture_counts: List[int] = field(default_factory=lambda: [1, 10])
    step_counts: List[int] = field(default_factory=lambda: [200, 1200])
    replay_modes: List[str] = field(default_factory=lambda: ["none", "trajectory"])
    repetitions: int = 5
    smoke: bool = False
    output_dir: Path = field(default_factory=lambda: Path("backend/benchmarks/results"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_counts": self.worker_counts,
            "fixture_counts": self.fixture_counts,
            "step_counts": self.step_counts,
            "replay_modes": self.replay_modes,
            "repetitions": self.repetitions,
            "smoke": self.smoke,
            "output_dir": str(self.output_dir),
        }


@dataclass
class BenchmarkRunResult:
    """Metrics for a single configuration point across repetitions."""
    workers: int
    fixtures: int
    steps: int
    replay_mode: str
    repetitions: int
    elapsed_times: List[float] = field(default_factory=list)
    throughput_fixtures_per_sec: float = 0.0
    throughput_steps_per_sec: float = 0.0
    p50_latency_sec: float = 0.0
    p95_latency_sec: float = 0.0
    min_latency_sec: float = 0.0
    max_latency_sec: float = 0.0
    latency_spread_sec: float = 0.0
    result_hashes: List[str] = field(default_factory=list)
    correctness_pass: bool = True
    memory_peak_mb: Optional[float] = None

    def compute_statistics(self) -> None:
        if not self.elapsed_times:
            return
        times = sorted(self.elapsed_times)
        self.min_latency_sec = round(times[0], 4)
        self.max_latency_sec = round(times[-1], 4)
        self.latency_spread_sec = round(self.max_latency_sec - self.min_latency_sec, 4)
        self.p50_latency_sec = round(statistics.median(times), 4)

        if len(times) == 1:
            self.p95_latency_sec = self.p50_latency_sec
        else:
            # 95th percentile
            self.p95_latency_sec = round(statistics.quantiles(times, n=100, method='inclusive')[94], 4)

        total_fixtures = self.fixtures * self.repetitions
        total_time = sum(self.elapsed_times)
        if total_time > 0:
            self.throughput_fixtures_per_sec = round(total_fixtures / total_time, 2)
            self.throughput_steps_per_sec = round((total_fixtures * self.steps) / total_time, 2)

        # Check hash invariance across repetitions
        if len(set(self.result_hashes)) <= 1:
            self.correctness_pass = True
        else:
            self.correctness_pass = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workers": self.workers,
            "observed_workers": getattr(self, "observed_workers", 1),
            "fixtures": self.fixtures,
            "steps": self.steps,
            "replay_mode": self.replay_mode,
            "repetitions": self.repetitions,
            "elapsed_times": [round(t, 4) for t in self.elapsed_times],
            "throughput_fixtures_per_sec": self.throughput_fixtures_per_sec,
            "throughput_steps_per_sec": self.throughput_steps_per_sec,
            "p50_latency_sec": self.p50_latency_sec,
            "p95_latency_sec": self.p95_latency_sec,
            "min_latency_sec": self.min_latency_sec,
            "max_latency_sec": self.max_latency_sec,
            "latency_spread_sec": self.latency_spread_sec,
            "result_hashes": self.result_hashes,
            "correctness_pass": self.correctness_pass,
            "memory_peak_mb": self.memory_peak_mb,
        }


class BenchmarkRunner:
    """Executes benchmark suites and enforces correctness verification."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.machine_meta = get_machine_metadata()

    def run_single_simulation(
        self,
        fixture_idx: int,
        steps: int,
        replay_mode: str,
        seed: int,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Execute one match simulation and return (result_dict, output_hash).
        Uses Canonical GRFMatchExecutor if available, or deterministic synthetic sim in smoke mode.
        """
        if self.config.smoke:
            # Deterministic synthetic football simulation for fast CI benchmark
            import random
            rng = random.Random(seed)
            home_goals = rng.randint(0, 3)
            away_goals = rng.randint(0, 2)
            possession = [round(45.0 + rng.uniform(-10, 10), 1), round(55.0 - rng.uniform(-10, 10), 1)]
            shots = [rng.randint(home_goals, home_goals + 8), rng.randint(away_goals, away_goals + 5)]
            result = {
                "fixture_idx": fixture_idx,
                "steps": steps,
                "score": [home_goals, away_goals],
                "possession": possession,
                "shots": shots,
                "replay_mode": replay_mode,
            }
            # Simulate step calculation time
            time.sleep(0.001 * min(steps, 20))
            digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
            return result, digest

        # Standard in-engine simulation using Canonical GRFMatchExecutor
        from logic.simulation.match_executor import GRFMatchExecutor, SimulationSpec, ReplayMode
        spec = SimulationSpec(
            fixture_id=f"bench_fix_{fixture_idx}",
            season_year=2026,
            home_team_name="Benchmark Arsenal",
            away_team_name="Benchmark Chelsea",
            home_team_id=1,
            away_team_id=2,
            max_steps=steps,
            seed_val=seed,
            replay_mode=ReplayMode(replay_mode) if replay_mode in ReplayMode._value2member_map_ else ReplayMode.NONE,
        )
        executor = GRFMatchExecutor(spec)
        res = executor.execute()
        res_dict = res.to_dict()
        digest = hashlib.sha256(json.dumps(res_dict, sort_keys=True, default=str).encode()).hexdigest()
        return res_dict, digest

    def run_fixture_batch(self, workers, fixtures, steps, replay_mode, repetition):
        if self.config.smoke:
            from concurrent.futures import ThreadPoolExecutor
            import threading
            active, peak = 0, 0
            lock = threading.Lock()
            def run(index):
                nonlocal active, peak
                with lock:
                    active += 1
                    peak = max(peak, active)
                try:
                    return self.run_single_simulation(index, steps, replay_mode, 42000 + index)[1]
                finally:
                    with lock:
                        active -= 1
            with ThreadPoolExecutor(max_workers=workers) as pool:
                hashes = list(pool.map(run, range(fixtures)))
            return hashes, peak
        from logic.grf_batch_runner import GRFBatchRunner
        runner = GRFBatchRunner()
        if not runner.is_available():
            raise RuntimeError('Native GRF benchmark requires the configured WSL runtime')
        corpus = [{'match_id': f'bench_fix_{index}', 'home_team': 'Benchmark Arsenal',
                   'away_team': 'Benchmark Chelsea', 'home_team_id': 1, 'away_team_id': 2,
                   'seed_val': 42000 + index} for index in range(fixtures)]
        native = runner.run_matchday(corpus, max_steps=steps, worker_count=workers,
                                    run_id=f'bench_{workers}_{fixtures}_{steps}_{replay_mode}_{repetition}',
                                    output_root=self.output_dir / 'artifacts', render_mode='3d',
                                    record_states=replay_mode == 'full_state')
        hashes, edges = [], []
        for result in native:
            canonical = {key: result.get(key) for key in ('match_id', 'score', 'events', 'shots',
                                                        'possession', 'xg', 'passes_attempted', 'passes_completed')}
            hashes.append(hashlib.sha256(json.dumps(canonical, sort_keys=True, default=str).encode()).hexdigest())
            timing = result.get('_execution', {})
            if timing:
                edges.extend([(timing['started'], 1), (timing['ended'], -1)])
        active, peak = 0, 0
        for _, delta in sorted(edges):
            active += delta
            peak = max(peak, active)
        if peak == 0:
            raise RuntimeError('Benchmark returned no observed worker timings')
        return hashes, peak

    def run_suite(self) -> Dict[str, Any]:
        """Runs the entire benchmark matrix and records structured metrics."""
        results: List[BenchmarkRunResult] = []
        t_suite_start = time.perf_counter()

        for workers in self.config.worker_counts:
            for fixtures in self.config.fixture_counts:
                for steps in self.config.step_counts:
                    for r_mode in self.config.replay_modes:
                        run_res = BenchmarkRunResult(
                            workers=workers,
                            fixtures=fixtures,
                            steps=steps,
                            replay_mode=r_mode,
                            repetitions=self.config.repetitions,
                        )

                        for rep in range(self.config.repetitions):
                            t0 = time.perf_counter()
                            hashes, observed = self.run_fixture_batch(workers, fixtures, steps, r_mode, rep)
                            run_res.observed_workers = max(getattr(run_res, 'observed_workers', 0), observed)

                            elapsed = time.perf_counter() - t0
                            run_res.elapsed_times.append(elapsed)
                            combined_hash = hashlib.sha256("".join(hashes).encode()).hexdigest()
                            run_res.result_hashes.append(combined_hash)

                        run_res.compute_statistics()
                        results.append(run_res)

        t_suite_end = time.perf_counter()
        suite_duration = round(t_suite_end - t_suite_start, 3)

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "machine_metadata": self.machine_meta,
            "benchmark_config": self.config.to_dict(),
            "workload": "synthetic_concurrent" if self.config.smoke else "native_grf_pool",
            "suite_duration_seconds": suite_duration,
            "results": [r.to_dict() for r in results],
            "all_passed": all(r.correctness_pass for r in results),
        }
        # Worker topology must not change outcomes for the same fixture corpus.
        groups = {}
        for result in results:
            key = (result.fixtures, result.steps, result.replay_mode)
            groups.setdefault(key, set()).update(result.result_hashes)
        report['topology_invariance'] = all(len(hashes) == 1 for hashes in groups.values())
        report['all_passed'] = report['all_passed'] and report['topology_invariance']

        # Persist report to isolated output directory
        report_file = self.output_dir / f"benchmark_report_{int(time.time())}.json"
        report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["saved_path"] = str(report_file)

        return report
