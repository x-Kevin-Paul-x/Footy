#!/usr/bin/env python3
"""
CLI Runner for Footy Benchmark Suite.
Usage:
    python backend/benchmarks/run_benchmark.py --smoke
    python backend/benchmarks/run_benchmark.py --workers 1,2,4 --fixtures 1,10 --repetitions 3
"""

import sys
import os
import argparse
from pathlib import Path

# Ensure backend/src is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
SRC_DIR = BACKEND_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from benchmarks.benchmark_harness import BenchmarkConfig, BenchmarkRunner


def parse_args():
    parser = argparse.ArgumentParser(description="Footy Benchmark and Performance Suite")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run lightweight smoke benchmark for quick CI correctness verification",
    )
    parser.add_argument(
        "--workers",
        type=str,
        default="1,2,4",
        help="Comma-separated list of worker counts to benchmark (e.g., '1,2,4')",
    )
    parser.add_argument(
        "--fixtures",
        type=str,
        default="1,10",
        help="Comma-separated list of fixture counts (e.g., '1,10')",
    )
    parser.add_argument(
        "--steps",
        type=str,
        default="200,1200",
        help="Comma-separated list of simulation step counts (e.g., '200,1200')",
    )
    parser.add_argument(
        "--replay-modes",
        type=str,
        default="none,trajectory",
        help="Comma-separated list of replay modes (e.g., 'none,trajectory')",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=None,
        help="Number of repetitions per configuration point (default: 5, or 1 in smoke mode)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(BACKEND_DIR / "benchmarks" / "results"),
        help="Output directory for structured benchmark results",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    workers = [int(w.strip()) for w in args.workers.split(",") if w.strip()]
    fixtures = [int(f.strip()) for f in args.fixtures.split(",") if f.strip()]
    steps = [int(s.strip()) for s in args.steps.split(",") if s.strip()]
    replay_modes = [r.strip() for r in args.replay_modes.split(",") if r.strip()]

    if args.smoke:
        repetitions = args.repetitions or 1
        workers = [1, 2]
        fixtures = [1, 5]
        steps = [100, 200]
        replay_modes = ["none"]
    else:
        repetitions = args.repetitions or 5

    config = BenchmarkConfig(
        worker_counts=workers,
        fixture_counts=fixtures,
        step_counts=steps,
        replay_modes=replay_modes,
        repetitions=repetitions,
        smoke=args.smoke,
        output_dir=Path(args.output_dir),
    )

    print("=" * 70)
    print(" FOOTY PERFORMANCE BENCHMARK SUITE")
    print(f" Mode: {'SMOKE (Fast CI)' if config.smoke else 'FULL ENGINE'}")
    print(f" Workers: {config.worker_counts} | Fixtures: {config.fixture_counts} | Steps: {config.step_counts}")
    print(f" Repetitions: {config.repetitions} | Output: {config.output_dir}")
    print("=" * 70)

    runner = BenchmarkRunner(config)
    report = runner.run_suite()

    print("\n--- RESULTS TABLE ---")
    header = f"{'Workers':>7} | {'Fixtures':>8} | {'Steps':>6} | {'Replay':>10} | {'P50 (s)':>8} | {'P95 (s)':>8} | {'Fixt/s':>8} | {'Correct?':>8}"
    print(header)
    print("-" * len(header))

    for r in report["results"]:
        status = "PASS" if r["correctness_pass"] else "FAIL"
        print(
            f"{r['workers']:>7} | {r['fixtures']:>8} | {r['steps']:>6} | {r['replay_mode']:>10} | "
            f"{r['p50_latency_sec']:>8.3f} | {r['p95_latency_sec']:>8.3f} | "
            f"{r['throughput_fixtures_per_sec']:>8.1f} | {status:>8}"
        )

    print("-" * len(header))
    print(f"Total benchmark time: {report['suite_duration_seconds']}s")
    print(f"Report saved to: {report.get('saved_path')}")

    if not report["all_passed"]:
        print("\n[ERROR] Correctness check failed on one or more configurations!")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All benchmark configurations passed determinism and performance gates.")
        sys.exit(0)


if __name__ == "__main__":
    main()
