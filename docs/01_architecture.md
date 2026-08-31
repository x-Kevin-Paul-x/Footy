# 01. System Architecture

## Overview
**Footy** is an intelligent full-stack football simulation, analytics, and AI manager platform. It combines a high-fidelity Python match engine, PyTorch Deep Reinforcement Learning (DQN) manager agents, Google Research Football (GRF) 11v11 physics-based match simulation, and a retro-tactile React dashboard.

---

## The Core Architectural Principle
> [!IMPORTANT]
> **"The Simulation Produces Truth. Everything Else Consumes That Truth."**
> 
> In Footy, simulation physics, match statistics, database records, and video broadcast replays are strictly decoupled. Simulation never performs video rendering, and replay never re-simulates physics. All downstream consumers read from a single, canonical, immutable `MatchTrajectory`.

---

## Target System Architecture

```mermaid
graph TD
    subgraph FootyLayer ["Footy Domain Layer"]
        League[League Engine & Scheduler]
        ManagerAI[Manager AI & PyTorch DQN Brain]
        Squads[Squads, Lineups & Player Ratings]
        Tactics[Team Tactics & Formation Coordinates]
    end

    subgraph AdapterLayer ["Footy GRF Adapter"]
        Adapter[FootyGRFAdapter]
        ProfileMap[Player Attribute -> GRF Modifier Mapper]
        Perspective[Perspective-Aware Feature Extractor]
    end

    subgraph SimLayer ["Phase A: Fast Simulation Core (0 Rendering)"]
        WorkerPool[Persistent GRF Worker Pool]
        TiKick[TiKick 11v11 Recurrent MARL Policy]
        GRFEnv[Headless GRF Environment]
        BatchInference[Batched GPU/CPU Inference]
    end

    subgraph Artifact ["Single Source of Truth"]
        Trajectory[MatchTrajectory (.npz / Binary Keyframes)]
        Fingerprint[Simulation Fingerprint (SHA256)]
    end

    subgraph Downstream ["Phase B: Truth Consumers"]
        StatsEngine[Truth Statistics Engine (Opta Standards)]
        DB[(SQLite / football_sim.db)]
        ReplayRenderer[Broadcast Video Renderer (TV Overlays & Multi-Cam)]
        WebUI[React 18 Dashboard & 2D Tactical Board]
    end

    League --> Adapter
    ManagerAI --> Adapter
    Squads --> Adapter
    Tactics --> Adapter

    Adapter --> WorkerPool
    WorkerPool --> TiKick
    WorkerPool --> GRFEnv
    TiKick --> BatchInference

    GRFEnv --> Trajectory
    TiKick --> Trajectory
    Adapter --> Fingerprint

    Trajectory --> StatsEngine
    Trajectory --> ReplayRenderer
    StatsEngine --> DB
    StatsEngine --> WebUI
    ReplayRenderer --> WebUI
```

---

## Architectural Pillars

### 1. Unified Canonical GRF Engine
* Consolidates all simulation paths into one canonical engine (`FootyGRFSimulator`).
* Eliminates the split between `match_engine_grf.py` and `grf_native_runner.py`.
* Ensures that whether a match is triggered from the season batch runner, the API endpoint (`/api/v1/match/simulate-grf`), or CLI benchmarks, the exact same environment parameters, random seeds, and feature extractors are used.

### 2. Two-Phase Decoupled Pipeline (Simulate vs. Render)
* **Phase A — Pure Simulation (Headless & Fast)**:
  * Executes GRF physics and TiKick neural inference with `render=False`.
  * Generates 0 OpenCV frames and 0 video files.
  * Achieves high throughput ($500–2000+$ matches/hour on GPU batching).
  * Emits an immutable `MatchTrajectory` containing timestamps, coordinates, ball velocity, player IDs, and physics events.
* **Phase B — Replay & Broadcast Rendering (On-Demand)**:
  * Reads the pre-computed `MatchTrajectory`.
  * Draws pitch graphics, broadcast HUD cards, player names, and tactical radar.
  * Supports multiple virtual cameras (TV Main, Tactical Overhead, Behind Goal, Player Focus) and instant slow-motion replays without ever invoking the neural policy again.

### 3. Perspective-Aware Canonical Space
* Normalizes left-team and right-team observations into a **canonical attacking coordinate system**.
* Ensures the right-team agents receive correct symmetric observations ($X$-axis mirrored, team lists swapped) so both teams make decisions using identical neural state geometry.

### 4. Player Attribute & Tactical Mapping Layer
* Converts Footy's Football Manager-style attributes (Pace, Shooting, Passing, Tackling, Stamina, Strength) into calibrated physical and action-selection modifiers.
* Translates tactical formations (`4-3-3`, `4-2-3-1`, `3-5-2`) into initial pitch spatial coordinates and dynamic defensive anchors.

### 5. Truth-Based Statistics Conservation
* All match stats (goals, shots, shots on target, possession %, passes, fouls) are derived directly from the physical collision and trajectory events.
* Eliminates fabricated placeholders (e.g. hardcoded 350 passes or $xG = \text{Goals} \times 0.75$).

---

## High-Level Component Structure

| Component | Path | Responsibility |
| :--- | :--- | :--- |
| **FastAPI REST API** | `backend/src/api_fastapi.py` | Asynchronous API serving league data, squad rosters, job queues, and video streaming. |
| **Footy GRF Adapter** | `backend/src/logic/footy_grf_adapter.py` | Maps Footy players, tactics, and formations into GRF simulation configs. |
| **Canonical GRF Engine** | `backend/src/logic/grf_simulator.py` | Core headless 11v11 simulation loop with perspective normalization. |
| **Trajectory Store** | `backend/src/logic/trajectory.py` | Serialization, compression, and deserialization of `.npz` match trajectories. |
| **Broadcast Renderer** | `backend/src/logic/broadcast_renderer.py` | Decoupled video generator with multi-camera director and TV overlays. |
| **PyTorch DQN Manager** | `backend/src/ml/dqn_agent.py` | Tactical RL agent deciding team formations, training regimens, and substitutions. |
| **Database & ORM** | `backend/src/database/` | SQLite database managed with SQLAlchemy models and Alembic migrations. |
| **React Dashboard** | `frontend/src/` | Tactile retro UI, 2D tactic board, FM attribute pentagons, and replay player. |

---

## Directory Organization

```
Footy/
├── .agents/skills/               # Antigravity Expert Skills
│   ├── grf-deterministic-engine/ # Replay parity & trajectory logging
│   ├── grf-environment-diagnostics/ # WSL2, headless EGL & PyTorch health
│   ├── match-engine-balancer/    # Opta statistical calibration
│   ├── rl-manager-trainer/       # PyTorch DQN manager trainer
│   ├── multi-season-stability-tester/ # Multi-season economy & squad stress tests
│   ├── fullstack-feature-scaffold/ # Fullstack recipe (DB -> FastAPI -> React)
│   └── alembic-sqlite-guardian/  # Safe SQLite migrations
├── backend/
│   ├── alembic/                  # Alembic migration scripts
│   ├── checkpoints/              # Model weights (TiKick actor.pt, DQN dqn_best.pt)
│   ├── data/                     # Database files (football_sim.db)
│   ├── reports/                  # Trajectories (.npz), JSON reports, MP4 videos
│   │   ├── recordings/
│   │   ├── season_reports/
│   │   └── transfer_logs/
│   ├── src/
│   │   ├── api_fastapi.py        # REST API endpoints & WebSocket feeds
│   │   ├── config.py             # System paths, constants & GPU configs
│   │   ├── database/             # SQLAlchemy models & repository helpers
│   │   ├── logic/                # Simulation core, adapter, trajectory & renderer
│   │   ├── main.py               # Multi-season orchestrator CLI
│   │   ├── ml/                   # Manager DQN policy, reward & state encoder
│   │   ├── models/               # Domain models (Player, Team, League, Manager)
│   │   └── schemas.py            # Pydantic v2 schemas
│   └── tests/                    # Pytest verification test suite
├── frontend/
│   ├── src/
│   │   ├── components/           # FormationViewer, Pitch, MatchVideoReplay
│   │   ├── pages/                # Dashboard, Squad, Tactics, Replays, Benchmarks
│   │   ├── services/             # Axios API client & WebSocket connections
│   │   └── store/                # Zustand state management
│   ├── package.json
│   └── vite.config.ts
└── docs/                         # System Documentation & Developer Guides
```
