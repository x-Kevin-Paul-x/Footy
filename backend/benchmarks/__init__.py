"""
Footy Benchmark Suite and Performance Gate.
Provides standardized measurement harnesses for simulation throughput, latency percentiles (p50/p95),
resource utilization, and determinism verification.
"""

from .benchmark_harness import (
    BenchmarkConfig,
    BenchmarkRunResult,
    BenchmarkRunner,
    get_machine_metadata,
)

__all__ = [
    "BenchmarkConfig",
    "BenchmarkRunResult",
    "BenchmarkRunner",
    "get_machine_metadata",
]
