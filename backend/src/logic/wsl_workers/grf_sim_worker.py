"""
WSL Dedicated Worker: Pure GRF + TiKick MARL Match Simulation.
Executes 11v11 MARL physics using canonical GRFMatchExecutor.
Outputs compact .npz trajectory, raw .dump trace, and verified MatchManifest JSON.
Supports both one-shot CLI execution and persistent daemon mode.
"""

import os
import sys
import json
import time
from typing import Dict, Any, Optional

# Ensure backend/src and third-party modules can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_src = os.path.dirname(os.path.dirname(script_dir))
if backend_src not in sys.path:
    sys.path.insert(0, backend_src)

from logic.simulation.match_executor import GRFMatchExecutor, ReplayMode, SimulationSpec, CanonicalMatchResult
from logic.simulation.policy_backend import CPUSinglePolicy

_CANONICAL_POLICY = None
_CANONICAL_POLICY_KEY = None


def run_simulation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute match simulation using canonical GRFMatchExecutor.

    Ensures single-match API calls, daemons, and matchday batches share the exact same
    executor, event reducer, and seeding logic.
    """
    global _CANONICAL_POLICY, _CANONICAL_POLICY_KEY

    key = (str(payload.get("ckpt_path", "")), str(payload.get("tikick_dir", "")))
    if _CANONICAL_POLICY is None or _CANONICAL_POLICY_KEY != key:
        _CANONICAL_POLICY = CPUSinglePolicy(ckpt_path=key[0], tikick_dir=key[1])
        _CANONICAL_POLICY_KEY = key

    replay_mode = ReplayMode.FULL_STATE if payload.get("states_file") else ReplayMode.TRAJECTORY
    worker = None
    try:
        worker = GRFMatchExecutor(
            payload,
            max_steps=int(payload.get("max_steps", 1200)),
            replay_mode=replay_mode,
        )
        _CANONICAL_POLICY.reset_match(worker.match_id, worker.seed_val)
        observations = worker.get_initial_observations()
        done = False
        while not done and worker.step_idx < worker.max_steps:
            actions = _CANONICAL_POLICY.evaluate(observations, match_ids=[worker.match_id])
            observations, done, _ = worker.step(actions)
        res = worker.finalize()
        return res.to_dict() if hasattr(res, "to_dict") else res
    except Exception:
        if worker is not None:
            worker.close()
        raise


def _legacy_run_simulation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Deprecated legacy simulation entrypoint forwarded to canonical run_simulation."""
    return run_simulation(payload)


def run_daemon_server(port: int = 58210):
    """
    Persistent daemon mode: keeps TiKick PyTorch weights resident in memory
    and processes match simulation requests over a local TCP socket.
    """
    import socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(5)
    print(f"GRF_SIM_DAEMON_READY:{port}", flush=True)
    response_cache: Dict[str, Dict[str, Any]] = {}
    max_request_bytes = int(os.environ.get("FOOTY_DAEMON_MAX_REQUEST_BYTES", str(2 * 1024 * 1024)))

    while True:
        try:
            conn, _ = server.accept()
            with conn:
                data_bytes = b""
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    data_bytes += chunk
                    if len(data_bytes) > max_request_bytes:
                        raise ValueError("Simulation daemon request exceeds configured size limit")
                    if b"\n" in data_bytes:
                        break

                if not data_bytes.strip():
                    continue

                payload = json.loads(data_bytes.decode('utf-8').strip())
                if payload.get("command") == "shutdown":
                    conn.sendall(b"OK\n")
                    break

                request_id = str(payload.get("request_id", ""))
                if request_id and request_id in response_cache:
                    res = response_cache[request_id]
                else:
                    res = run_simulation(payload)
                    if request_id:
                        response_cache[request_id] = res
                        if len(response_cache) > 128:
                            response_cache.pop(next(iter(response_cache)))
                resp_bytes = json.dumps(res).encode('utf-8') + b"\n"
                conn.sendall(resp_bytes)
        except Exception as e:
            sys.stderr.write(f"Daemon error: {e}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 58210
        run_daemon_server(port)
    else:
        payload_str = sys.argv[1]
        if os.path.exists(payload_str):
            with open(payload_str, "r", encoding="utf-8") as f:
                args = json.load(f)
        else:
            args = json.loads(payload_str)
        res = run_simulation(args)
        print("MATCH_SIM_RESULT_JSON:" + json.dumps(res))
