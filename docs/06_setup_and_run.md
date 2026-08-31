# 06. Setup & Execution Guide

This guide provides instructions to set up the development environment, configure Google Research Football (GRF) and TiKick in WSL2, run the FastAPI backend, launch the React frontend, and execute simulation tests.

---

## Prerequisites

* **Windows 11 / Linux (Ubuntu 22.04 LTS / 24.04 LTS)**
* **Python**: 3.10 or higher
* **Node.js**: 18.0 or higher (with `npm`)
* **NVIDIA GPU with CUDA Support** *(Recommended for batched TiKick inference)*
* **WSL2** *(For Windows host running GRF C++ engine)*

---

## 1. Environment Setup

### Step A: Configure Environment Variables
```bash
# Windows PowerShell
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env

# Linux / macOS
cp .env.example .env
cp frontend/.env.example frontend/.env
```

### Step B: Host Python Virtual Environment
```powershell
# Create and activate virtual environment
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# Install core backend dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Optional: Install ML & PyTorch dependencies
pip install -r requirements-ml.txt
```

### Step C: WSL2 GRF Environment Setup *(Windows)*
```bash
# Inside WSL2 Ubuntu:
sudo apt-get update && sudo apt-get install -y \
    git cmake build-essential libgl1-mesa-dev libsdl2-dev \
    libsdl2-image-dev libsdl2-ttf-dev libsdl2-gfx-dev \
    libboost-all-dev libdirectfb-dev libst-dev mesa-utils \
    xvfb libosmesa6-dev python3-pip python3-venv ffmpeg

# Create dedicated WSL virtual environment
python3 -m venv /root/venv_baller
source /root/venv_baller/bin/activate
pip install gfootball torch numpy opencv-python imageio imageio-ffmpeg
```

---

## 2. Running the Application

### Option 1: FastAPI Backend Server
```powershell
# Run backend development server (Port 5001)
python backend/src/dev_server.py
```
* **Interactive API Docs**: `http://localhost:5001/docs` (Swagger UI)
* **Health Check**: `http://localhost:5001/health`

### Option 2: React Frontend Development Server
```powershell
cd frontend
npm install
npm run dev
```
* **Web Dashboard**: `http://localhost:5173`

---

## 3. Database Migrations (Alembic)

```powershell
# Run pending database migrations
alembic -c backend/alembic.ini upgrade head

# Generate a new migration after modifying database/models.py
alembic -c backend/alembic.ini revision --autogenerate -m "add_trace_file_column"
```

---

## 4. Running Simulations & Benchmarks

### A. Run 10-Match Matchday Simulation
```powershell
$env:PYTHONPATH="backend/src"; python backend/src/main.py
```

### B. Run Deterministic Replay Parity Test
```powershell
$env:PYTHONPATH="backend/src"; python scratch/test_10_matches_and_3_replays.py
```

### C. Run PyTorch DQN Manager Benchmarking
```powershell
$env:PYTHONPATH="backend/src"; python backend/src/ml/evaluation.py
```

---

## 5. Automated Test Suite

```powershell
# Run all backend unit and integration tests
$env:PYTHONPATH="backend/src"; pytest backend/tests/ -v

# Run GRF-specific engine and trajectory tests
$env:PYTHONPATH="backend/src"; pytest backend/tests/test_grf_engine.py -v
```

---

## 6. Antigravity Workspace Diagnostics

You can invoke specialized workspace skills directly to audit subsystems:
* `grf-deterministic-engine`: Diagnostic checks for `.npz` trajectory logging and replay parity.
* `grf-environment-diagnostics`: WSL2 health check, OpenGL/EGL headless driver verification.
* `match-engine-balancer`: Opta statistical calibration ($xG$, goal distributions, foul frequency).
* `rl-manager-trainer`: PyTorch DQN training loop and reward diagnostics.
