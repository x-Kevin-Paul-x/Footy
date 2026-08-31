# Comprehensive Footy & GRF Architecture Refactor Plan

Based on a deep audit of the `feat/grf-3d-broadcast-replay` branch, it is clear that optimizing the current implementation (e.g., speeding up OpenCV or NumPy allocations) would be a mistake. The primary issues are architectural and correctness-based. The simulation loop is currently performing rendering, producing fake statistics, ignoring API parameters, and suffering from a critical policy perspective bug.

This document outlines the **P0 (Correctness & Core Architecture)** and **P1 (Integration & Performance Foundations)** refactor plans.

---

## 🔴 P0: Correctness & Core Architecture Fixes

The goal of P0 is to make the GRF simulation mathematically correct, statistically honest, and architecturally sound before any visual or performance optimizations occur.

### 1. Fix the TiKick Perspective Bug (`logic/grf_native_runner.py` & `logic/match_engine_grf.py`)
**The Problem:** `extract_features_268` hardcodes `ally` as `left_team` and `enemy` as `right_team` for all agents, causing the Away (right) team policy to receive inverted observations.
**The Fix:**
Rewrite `extract_features_268` to accept a `team_side` parameter ("left" or "right").
```python
def extract_features(raw_obs, team_side="left", num_agents=10, ...):
    if team_side == "left":
        ally = np.array(raw_obs[0]['left_team'])
        enemy = np.array(raw_obs[0]['right_team'])
        ally_dir = np.array(raw_obs[0]['left_team_direction'])
        enemy_dir = np.array(raw_obs[0]['right_team_direction'])
    else:
        ally = np.array(raw_obs[0]['right_team'])
        enemy = np.array(raw_obs[0]['left_team'])
        ally_dir = np.array(raw_obs[0]['right_team_direction'])
        enemy_dir = np.array(raw_obs[0]['left_team_direction'])

        # MUST mirror coordinates (X-axis) so the right team sees themselves
        # attacking in the same canonical direction as the left team.
        ally[:, 0] = -ally[:, 0]
        enemy[:, 0] = -enemy[:, 0]
        # (Mirror directions and ball coordinates similarly)
```

### 2. Consolidate to a Single Canonical Engine
**The Problem:** The API calls `grf_native_runner.py` (which spawns WSL), while `match_engine_grf.py` contains a separate `FootyMatchSimulator` implementation. They produce different results and use different seeds.
**The Fix:**
Delete or deprecate the duplicated logic. Establish `match_engine_grf.py` as the *only* entry point for GRF simulation. If WSL is strictly required for TiKick execution on Windows, `match_engine_grf.py` should act as the client to a persistent WSL worker, rather than re-implementing the loop natively.

### 3. Replace Re-Simulation with True Trajectory Replay
**The Problem:** Requesting a replay currently triggers a completely new match simulation that happens to have the same `match_id`.
**The Fix:**
Create a `MatchTrajectory` data structure.
During simulation, record states (ball, players) to an efficient binary format (e.g., `.npz` or HDF5) and save it to `RECORDINGS_DIR`.
When `/api/v1/match/{match_id}/video` is called, it should *not* simulate. It should invoke a new `render_replay(trajectory_file)` function that reads the saved states and draws frames.

### 4. Fix Fabricated Statistics and Scorer Logic
**The Problem:** xG is calculated as `score * 0.75`. Shots are incremented when a goal is scored. The "scorer" is just the currently active player.
**The Fix:**
- Remove the fake xG and shot counts from `run_match` and `FootyMatchSimulator`.
- Hook into GRF's internal event system (if exposed) or write a robust heuristic during the simulation loop to detect genuine shot events (action == 12).
- Calculate xG based on shot location coordinates (distance, angle).
- Identify the scorer by tracking the last player to possess the ball before the score changed.

### 5. Respect API Parameters
**The Problem:** `req.generate_video` and `req.max_steps` are ignored in `/api/v1/match/simulate-grf`.
**The Fix:**
Wire the `MatchSimulationRequest` parameters directly into the engine call, enforcing bounds.

---

## 🟠 P1: Integration & Performance Foundations

Once the simulation is producing correct, verifiable trajectories, move to integration and performance.

### 1. Build the `FootyGRFAdapter` (Connecting Attributes & Tactics)
**The Problem:** Currently, Footy player ratings (pace, shooting) and team formations (4-3-3) are passed in name only, having zero effect on the physics simulation.
**The Fix:**
Create an adapter class:
```python
class FootyGRFAdapter:
    def map_player_attributes(self, footy_player) -> dict:
        # Map 1-99 Footy ratings to GRF physical modifiers (speed, stamina)
        pass

    def apply_formation(self, env, team_side, formation_string):
        # Position players at kickoff/resets according to FORMATION_COORDINATES
        pass
```

### 2. Extract Rendering from the Simulation Loop (Crucial!)
**The Problem:** `cv2` rectangle drawing and video encoding happen inside the tight GPU neural network inference loop.
**The Fix:**
Introduce strict separation:
- **Phase A (Simulate):** Run GRF + TiKick as fast as possible. Save `MatchTrajectory`.
- **Phase B (Render):** A separate background task reads the trajectory and produces the `.mp4` file.
This allows simulations to run at thousands of steps per second.

### 3. Implement Persistent GRF Workers (Eliminate Process Overhead)
**The Problem:** `subprocess.run(["wsl", ...])` is called for every match, re-initializing Python, loading PyTorch, and loading the 256mb TiKick weights every time.
**The Fix:**
Create a long-running worker script (e.g., `grf_worker.py`) that loads PyTorch once and listens on a socket or queue (e.g., Redis or ZeroMQ) for match configuration payloads. FastAPI submits jobs to the worker pool and awaits the results.

### 4. Vectorize Feature Extraction and Batch Inference
**The Problem:** Python `extend`, `.copy()`, and `flatten()` are called millions of times per match. Inference is done one batch of 20 agents at a time.
**The Fix:**
- Preallocate a fixed NumPy array `obs = np.zeros((20, 268), dtype=np.float32)` and update it in-place using array slicing.
- (Later optimization): If simulating a full season, batch observations from *multiple matches* into a single GPU tensor (e.g., `[640, 268]`) to fully utilize the GPU. Use `torch.inference_mode()`.

---

## Conclusion

The core vision of integrating GRF with Footy is excellent. However, the simulation must be treated as the ultimate source of truth. **Stop rendering during simulation, fix the TiKick perspective bug, stop faking match statistics, and ensure player attributes actually affect the physics environment.**
