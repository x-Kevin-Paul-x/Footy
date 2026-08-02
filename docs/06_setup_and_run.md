# 06. Setup and Run Guide

Follow these instructions to set up the development environment and run the Footy Project.

## Prerequisites

*   **Python 3.8+**
*   **Node.js 16+** & **npm**

## 1. Backend Setup

1.  Navigate to the root directory.
2.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
3.  Optional shell configuration:
    ```bash
    copy .env.example .env
    ```
    The backend reads `FOOTY_API_PORT`, `FOOTY_API_DEBUG`, `FOOTY_NUM_SEASONS`, and `FOOTY_SIMULATION_TIMEOUT_SECONDS` from the shell environment when the Python process starts.

### Running the Simulation (Standalone)
To run the simulation without the UI (useful for testing logic):
```bash
$env:PYTHONPATH="backend/src"; python backend/src/main.py
```
This will:
*   Reset the database (`football_sim.db`).
*   Simulate the configured number of seasons (default: 10, configurable via `FOOTY_NUM_SEASONS`).
*   Generate report files in `backend/reports/season_reports/`.

### Running the API
To serve data to the frontend:
```bash
$env:PYTHONPATH="backend/src"; python backend/src/api_fastapi.py
```
The API will start on `http://localhost:5001`.

## 2. Frontend Setup

1.  Navigate to the `frontend/` directory:
    ```bash
    cd frontend
    ```
2.  Install Node dependencies:
    ```bash
    npm install
    ```
3.  Optional Vite environment override:
    ```bash
    copy .env.example .env
    ```
    Set `VITE_API_BASE_URL` if the API is not running on `http://localhost:5001`.

### Running the Frontend
Start the development server:
```bash
npm run dev
```
Access the application at `http://localhost:5173`.

## 3. Running the Full System

1.  **Terminal 1 (API)**:
    ```bash
    $env:PYTHONPATH="backend/src"; python backend/src/api_fastapi.py
    ```
2.  **Terminal 2 (Frontend)**:
    ```bash
    cd frontend
    npm run dev
    ```
3.  Open your browser to the local URL provided by Vite (usually `http://localhost:5173`).
4.  In the Dashboard, look for a "Run Simulation" button to trigger `main.py` via the API, or simply view the data if you ran `main.py` manually beforehand.

## 4. Running Tests

Install the development test dependency first:
```bash
pip install -r requirements-dev.txt
```

Then run backend tests from the project root:
```bash
$env:PYTHONPATH="backend/src"; pytest backend/tests/
```

## 5. Optional ML Setup

Install the optional ML stack if you want to use the supervised models or retrain the DQN agent:
```bash
pip install -r requirements-ml.txt
```

Notes:
*   `requirements-ml.txt` pins `scikit-learn==1.6.1` because the committed `match_predictor.pkl` and `market_valuator.pkl` artifacts were trained with that version.
*   The main simulation still runs without the ML extras; the optional stack is only required for model-backed valuation, RL training, and fast-mode match prediction workflows.

### Running the ML Training Pipeline

From the project root:
```bash
$env:PYTHONPATH="backend/src"; python backend/src/ml/train_pipeline.py
```

Useful variants:
```bash
$env:PYTHONPATH="backend/src"; python backend/src/ml/train_pipeline.py --skip-harvest
$env:PYTHONPATH="backend/src"; python backend/src/ml/train_rl.py train --episodes 100 --teams 6 --fast-mode
$env:PYTHONPATH="backend/src"; python backend/src/ml/train_rl.py eval --model ml/models/dqn_best.pt --episodes 10
$env:PYTHONPATH="backend/src"; python backend/src/ml/train_rl.py eval --model ml/models/dqn_best.pt --episodes 10 --fast-mode
$env:PYTHONPATH="backend/src"; python backend/src/ml/train_rl.py compare --models ml/models/dqn_best.pt ml/models/dqn_final.pt --episodes 10 --fast-mode
```

Evaluation notes:
*   `train_rl.py eval` now writes JSON benchmark reports to `ml/reports/`.
*   By default it compares the trained policy against `random` and `do_nothing` baselines so you can see whether the model is actually outperforming something trivial.
*   Use `--skip-baselines` if you only want the trained-policy summary.
*   `train_rl.py compare` evaluates multiple checkpoints in one run and ranks them by reward, points, and average finishing position.
*   The richer report output now includes reward volatility plus top-4 and title rates, which are better portfolio metrics than reward alone.
*   Once the backend API is running, the frontend `AI Benchmarks` page reads these saved JSON reports directly for demo-ready checkpoint comparisons.

## Troubleshooting

*   **Missing Dependencies**: If Python complains about missing modules, ensure you installed them: `names`, `numpy`, `flask`, `flask-cors`.
*   **ML Artifact Compatibility**: If you see a warning about `scikit-learn` artifact compatibility, install `requirements-ml.txt` or retrain the supervised models with the current environment.
*   **Port Conflicts**:
    *   API uses port **5001** by default. Override it with `FOOTY_API_PORT` if needed.
    *   Frontend uses port **5173** (default Vite).
*   **Database Errors**: If the database seems corrupted or schemas change, delete `backend/data/football_sim.db` and rerun the simulation bootstrap.
*   **API Connectivity**: If the frontend cannot reach the API, check `frontend/.env` and confirm `VITE_API_BASE_URL` matches the Flask port.
