# ⚽ Footy: Intelligent Football Simulation, GRF 3D Physics & AI Manager Engine

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Google Research Football](https://img.shields.io/badge/Google%20Research%20Football-11v11%20MARL-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://github.com/google-research/football)
[![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20RL%20%26%20TiKick-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![React](https://img.shields.io/badge/React-18.0+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4+-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **Footy** is an intelligent, full-stack football simulation, analytics, and management platform. It combines a high-speed stochastic match engine, **Google Research Football (GRF) 11v11 physics** with **TiKick Multi-Agent Reinforcement Learning (MARL)**, PyTorch Deep Q-Networks (DQN) manager brains, realistic transfer economics, and a tactile retro React dashboard with **cinematic 3D broadcast replays**.

---

## 🌟 Core Highlights

* 🎮 **Google Research Football (GRF) & TiKick MARL Physics**: Full 11v11 multi-agent physics simulation running neural policy self-play in headless environments.
* 🎬 **Decoupled 2-Phase Replay Architecture**: Simulation produces an immutable `MatchTrajectory` artifact; replays stream directly from recorded trajectories without re-evaluating policy, ensuring 100% scoreline and scorer parity.
* 🧠 **Deep Reinforcement Learning AI Managers**: PyTorch Deep Q-Networks (DQN) with action-masking make tactical adjustments, rotate squads, and negotiate transfers based on multi-season contextual rewards.
* 📐 **Perspective-Aware Coordinate Normalization**: Canonical attacking coordinate transforms guarantee mathematically symmetric policy behavior for both home and away agents.
* 💼 **Dynamic Transfer Market & Financial Ecosystem**: Age curves, youth academies, wage-to-turnover sustainability, stadium ticket revenues, and sponsorship scaling.
* 📊 **Opta-Grade Statistics Engine**: Real-time Expected Goals ($xG$), passing networks, shot qualities, stamina decay curves, and physical event tracking.
* 🎨 **Modern Tactile UI & Visualizers**: Interactive 2D tactical board (`FormationViewer.tsx`), FM-style attribute pentagons, Recharts financial graphs, and a cinematic broadcast highlight replayer.

---

## 🏗️ System Architecture

```mermaid
graph TD
    subgraph FootyDomain ["Footy Domain Layer"]
        League[League Engine & Scheduler]
        ManagerAI[Manager AI & PyTorch DQN Brain]
        Squads[Squads & Football Manager Attributes]
        Tactics[Team Tactics & Formation Coordinates]
    end

    subgraph AdapterLayer ["Footy GRF Adapter"]
        Adapter[FootyGRFAdapter]
        ProfileMap[Attribute -> Physical Modifier Map]
        Perspective[Perspective-Aware Normalizer]
    end

    subgraph SimCore ["Phase A: Fast Simulation Core (0 Rendering)"]
        WorkerPool[Persistent GRF Worker Pool]
        TiKick[TiKick 11v11 MARL Policy]
        GRFEnv[Headless GRF Physics]
    end

    subgraph Artifact ["Single Source of Truth"]
        Trajectory[MatchTrajectory (.npz / Binary Keyframes)]
    end

    subgraph Consumers ["Phase B: Truth Consumers"]
        Stats[Opta Statistics Engine]
        DB[(SQLite / football_sim.db)]
        Renderer[Cinematic Video Renderer (TV Overlays)]
        WebUI[React 18 Dashboard & 2D Tactic Board]
    end

    FootyDomain --> Adapter
    Adapter --> SimCore
    SimCore --> Trajectory
    Trajectory --> Stats
    Trajectory --> Renderer
    Stats --> DB
    Stats --> WebUI
    Renderer --> WebUI
```

---

## 🚀 Quick Start Guide

### Prerequisites
* **Windows 11 / Linux (Ubuntu 22.04 LTS / 24.04 LTS)**
* **Python**: `3.10` or higher
* **Node.js**: `18.0` or higher (with `npm`)
* **NVIDIA GPU with CUDA** *(Recommended for batched TiKick MARL)*
* **WSL2** *(For Windows host running GRF C++ engine)*

---

### 1. Local Environment Setup

#### Clone and Configure Environment
```bash
git clone https://github.com/x-Kevin-Paul-x/Footy.git
cd Footy

# Configure environment files
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env
```

#### Backend Python Virtual Environment
```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install core and dev dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### WSL2 GRF Setup *(For 3D Physics Simulation on Windows)*
```bash
# Inside WSL2 Ubuntu:
sudo apt-get update && sudo apt-get install -y \
    git cmake build-essential libgl1-mesa-dev libsdl2-dev \
    libsdl2-image-dev libsdl2-ttf-dev libboost-all-dev xvfb ffmpeg

python3 -m venv /root/venv_baller
source /root/venv_baller/bin/activate
pip install gfootball torch numpy opencv-python imageio imageio-ffmpeg
```

---

### 2. Running the Application

#### Start the FastAPI Backend (Port 5001)
```powershell
python backend/src/dev_server.py
```
* **Swagger API Docs**: `http://localhost:5001/docs`
* **Health Check**: `http://localhost:5001/health`

#### Start the React Frontend (Port 5173)
In a separate terminal:
```powershell
cd frontend
npm install
npm run dev
```
* **Web Application**: `http://localhost:5173`

---

## 🧪 Simulation, Benchmarks & Testing

### Run 10-Match Batch Simulation
```powershell
$env:PYTHONPATH="backend/src"; python backend/src/main.py
```

### Run Deterministic Replay Parity Test
```powershell
$env:PYTHONPATH="backend/src"; python scratch/test_10_matches_and_3_replays.py
```

### Run Pytest Test Suite
```powershell
$env:PYTHONPATH="backend/src"; pytest backend/tests/ -v
```

---

## 📁 Repository Structure

```text
Footy/
├── .agents/skills/             # Antigravity Expert Skills Suite
│   ├── grf-deterministic-engine/ # Replay parity & trajectory logging
│   ├── grf-environment-diagnostics/ # WSL2, headless EGL & PyTorch health
│   ├── match-engine-balancer/  # Opta statistical calibration
│   ├── rl-manager-trainer/     # PyTorch DQN manager trainer
│   ├── multi-season-stability-tester/ # Economy & squad stress tests
│   ├── fullstack-feature-scaffold/ # Fullstack recipe (DB -> FastAPI -> React)
│   └── alembic-sqlite-guardian/# Safe SQLite migrations
├── backend/
│   ├── alembic/                # Database migrations
│   ├── checkpoints/            # PyTorch DQN & TiKick policy weights
│   ├── data/                   # SQLite database (football_sim.db)
│   ├── reports/                # Match trajectories (.npz), reports, MP4 videos
│   ├── src/
│   │   ├── api_fastapi.py      # FastAPI routing & WebSockets
│   │   ├── config.py           # Application settings & environment vars
│   │   ├── database/           # SQLAlchemy models & CRUD operations
│   │   ├── logic/              # GRF simulation core, adapter, trajectory & renderer
│   │   ├── main.py             # CLI simulation driver
│   │   ├── ml/                 # PyTorch DQN policy & benchmarking
│   │   ├── models/             # Domain models (Team, Player, Match, League)
│   │   └── schemas.py          # Pydantic v2 schemas
│   └── tests/                  # Backend Pytest test suite
├── frontend/
│   ├── src/
│   │   ├── components/         # FormationViewer, Pitch, MatchVideoReplay
│   │   ├── pages/              # Dashboard, Squad, Tactics, Replays, Benchmarks
│   │   ├── services/           # Axios API client & WebSocket connections
│   │   └── store/              # Zustand state management
│   ├── package.json
│   └── vite.config.ts
└── docs/                       # Architectural guides & technical specifications
```

---

## 📜 Documentation Index

* **[01. System Architecture](docs/01_architecture.md)** — Master decoupled design & component overview.
* **[02. Backend Logic & Mechanics](docs/02_backend_logic.md)** — GRF physics, TiKick perspective symmetry, and trajectory specifications.
* **[03. Data Models & Schemas](docs/03_data_models.md)** — SQLAlchemy tables, trajectory binary formats, and Pydantic schemas.
* **[04. Frontend Guide](docs/04_frontend_guide.md)** — Tactical pitch visualization and broadcast replay player.
* **[05. Current Status & Audit](docs/05_current_status.md)** — Executive audit findings and P0–P3 roadmap.
* **[06. Setup & Execution](docs/06_setup_and_run.md)** — Step-by-step setup and test execution guide.

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

## 👨‍💻 Maintainer

* **Author**: Kevin Paul
* **GitHub**: [@x-Kevin-Paul-x](https://github.com/x-Kevin-Paul-x)
* **Repository**: [https://github.com/x-Kevin-Paul-x/Footy](https://github.com/x-Kevin-Paul-x/Footy)
