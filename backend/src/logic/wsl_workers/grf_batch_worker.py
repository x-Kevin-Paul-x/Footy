"""
WSL Dedicated Worker: Multi-Fixture Parallel Matchday Batch Simulator.
Executes authentic 11v11 MARL physics across concurrent GRF environments using:
- Next-Gen SimulationProcessPool (Multi-process scaling across CPU cores)
- Pluggable PolicyBackends (CPUSinglePolicy, CUDABatchPolicy)
- Fallback in-process sequential runner for debug/parity verification.
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np

# Ensure backend/src is on sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_src = os.path.dirname(os.path.dirname(script_dir))
if backend_src not in sys.path:
    sys.path.insert(0, backend_src)

from logic.simulation.simulation_process_pool import SimulationProcessPool
from logic.simulation.simulation_worker import ReplayMode


def run_batch_simulation(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Main entry point for batch matchday simulation.
    Routes to high-performance SimulationProcessPool.
    """
    fixtures = payload["fixtures"]
    ckpt_path = payload["ckpt_path"]
    tikick_dir = payload.get("tikick_dir", "")
    max_steps = int(payload.get("max_steps", 1200))
    backend_type = payload.get("backend_type", "cpu_single")
    num_workers = int(payload.get("num_workers", min(16, len(fixtures))))
    replay_mode_str = payload.get("replay_mode", "full_state")
    replay_mode = ReplayMode(replay_mode_str) if isinstance(replay_mode_str, str) else ReplayMode.FULL_STATE

    pool = SimulationProcessPool(
        num_workers=num_workers,
        backend_type=backend_type,
        use_affinity=payload.get("use_affinity", True)
    )

    results = pool.run_batch(
        fixtures=fixtures,
        ckpt_path=ckpt_path,
        tikick_dir=tikick_dir,
        max_steps=max_steps,
        replay_mode=replay_mode
    )

    return results


if __name__ == "__main__":
    payload_str = sys.argv[1]
    if os.path.exists(payload_str):
        with open(payload_str, "r", encoding="utf-8") as f:
            args = json.load(f)
    else:
        args = json.loads(payload_str)
    res = run_batch_simulation(args)
    print("MATCH_BATCH_SIM_RESULT_JSON:" + json.dumps(res))
