---
name: grf-deterministic-engine
description: >-
  Expert system for debugging, benchmarking, and maintaining 100% deterministic
  simulation-to-replay synchronization in Google Research Football (GRF) and TiKick MARL.
  Triggers when dealing with .dump files, video highlight generation, replay desyncs,
  or scoreboard attribution errors.
---

# Google Research Football (GRF) Deterministic Engine Guide

This skill provides protocols and procedures to guarantee that matches simulated in Google Research Football (GRF) produce **100% identical scores, match events, and goalscorer names** when replayed or rendered into video highlights.

---

## 1. Core Invariants & Physics Parity

### Invariant 1: Physics Step Parity
* When running simulations in GRF (`gfootball.env`), the physics engine steps at `physics_steps_per_frame = 1` by default.
* **Never override `physics_steps_per_frame` (e.g. to 10)** during replay or video rendering. Modifying the physics step rate alters internal collision detection, ball spin, and deflection angles, causing goals to turn into misses and vice versa.
* Always preserve the exact `config` dictionary saved in `replay[0]['debug']['config']`.

### Invariant 2: Random Seed Consistency
* Explicitly seed Python `random`, `numpy.random`, and `torch` with a deterministic seed derived from the `match_id`:
  ```python
  seed_val = int(hashlib.md5(f"match_{match_id}".encode()).hexdigest()[:8], 16) % 100000
  random.seed(seed_val)
  np.random.seed(seed_val)
  torch.manual_seed(seed_val)
  if torch.cuda.is_available():
      torch.cuda.manual_seed_all(seed_val)
  ```

---

## 2. Accurate Scorer & Event Tracking (MARL)

### The Problem with `raw_obs['active']`
In 11v11 Multi-Agent RL (controlling 10 outfield players simultaneously):
1. `raw_obs[0]['active']` is a single-agent artifact and resets to `0` or default center-forward during the goal celebration / kick-off reset state.
2. Relying on `active` when `curr_score > last_score` causes almost all goals to be incorrectly credited to player #8 or #9.

### The True Ball-Touch Tracker Protocol
Track the last active player who held ball possession on every single tick:

```python
# Updated on every simulation step:
ball_owned_team = raw_o['ball_owned_team']
ball_owned_player = raw_o['ball_owned_player']

if ball_owned_team == 0 and ball_owned_player != -1:
    last_home_touch_player = ball_owned_player  # index 1..10 in home roster
    last_touch_minute = match_min
elif ball_owned_team == 1 and ball_owned_player != -1:
    last_away_touch_player = ball_owned_player
    last_touch_minute = match_min

# When a goal is detected:
if curr_score[0] > last_score[0]:
    scorer_idx = last_home_touch_player if last_home_touch_player != -1 else 10
    scorer_name = home_players[min(scorer_idx, len(home_players) - 1)].split('(')[0].strip()
    events.append({
        "minute": match_min,
        "type": "goal",
        "team": "home",
        "player": scorer_name,
        "details": f"Goal! {scorer_name} scores for {home_team}!"
    })
```

---

## 3. Immutable Match Manifest Protocol

Never re-calculate scores or guess events during video rendering. The video renderer should be a **pure display pipe**:
1. Live simulation generates the official `Match Manifest` (final score, possession %, shots, and chronologically ordered events list).
2. The replay renderer receives this `Match Manifest` JSON.
3. The HUD and scoreboard overlay are drawn strictly from the manifest timestamps.

---

## 4. Trajectory Backup (`.npz`) Protocol

For instant, lightweight playback without invoking C++ GFootball replay loaders:
* Record all 22 player positions `(22, 2)` and ball `(3,)` into a compressed NumPy archive:
  ```python
  np.savez_compressed(
      f"backend/reports/recordings/traj_{match_id}.npz",
      coords=trajectory_array, # shape: (total_steps, 23, 2)
      manifest=json.dumps(manifest)
  )
  ```
* This `.npz` file ($\approx 100\text{ KB}$) can be directly read by custom 2D/3D renderers or frontend Canvas replays without WSL/GPU dependencies.
