# 06. Setup and Execution

Last verified: **6 September 2026**

## Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer and npm
- FFmpeg for encoded replay output
- On Windows, WSL2 with the configured GRF environment for real GRF tests and 3D rendering
- NVIDIA/CUDA is optional and should be selected only after representative benchmarks

## Host setup

```powershell
git clone https://github.com/x-Kevin-Paul-x/Footy.git
cd Footy

Copy-Item .env.example .env

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt

cd frontend
npm install
```

There is no checked-in `frontend/.env.example`. If an explicit development API URL is needed, create `frontend/.env` with:

```ini
VITE_API_BASE_URL=http://localhost:5001
```

The frontend client currently defaults to the same localhost URL in development.

## Backend and frontend

From the repository root:

```powershell
python backend/src/dev_server.py
```

- API documentation: `http://localhost:5001/docs`
- Health: `http://localhost:5001/api/v1/health`

From `frontend/`:

```powershell
npm run dev:frontend
```

- UI: `http://localhost:5173`

`npm run dev` starts both processes and assumes a valid Windows `.venv` at the repository root.

## Main environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `FOOTY_API_PORT` | `5001` | API port. |
| `FOOTY_API_DEBUG` | `false` | Debug mode. |
| `FOOTY_NUM_SEASONS` | `1` in code | CLI season count; the current `.env.example` sets 10. |
| `FOOTY_SIMULATION_TIMEOUT_SECONDS` | `1800` | External simulation timeout. |
| `FOOTY_DATA_DIR` | `backend/data` | Isolated DB root override, useful for tests. |
| `FOOTY_GRF_MAX_STEPS` | `1200` | Default GRF match steps. |
| `FOOTY_PARALLEL_WORKERS` | `10` | Requested match worker count. Benchmark before tuning. |
| `FOOTY_WSL_PYTHON` | `/root/venv_baller/bin/python3` | WSL interpreter. |
| `FOOTY_DEFAULT_RENDER_MODE` | `3d` | Default rendering mode. |
| `FOOTY_SYNC_VIDEO_RENDER` | `0` | Enable synchronous 3D video in batch payloads. |
| `FOOTY_RUN_RETENTION` | `0` | Runs to retain; zero keeps all historical run directories. |
| `FOOTY_TEMP_MAX_AGE_SECONDS` | `86400` | Age before stale temporary cleanup. |
| `FOOTY_MAX_MATCHES` | `0` | Optional shortened-run fixture cap. |

## Database warning

The current live database is at Alembic revision `879f4c01467a` and passed integrity and foreign-key checks. The Alembic chain cannot bootstrap an empty database: `alembic upgrade head` fails at `c7c6ac0ab9c1` because legacy tables do not exist.

Current fresh startup uses SQLAlchemy table creation and compatibility DDL. Do not test migrations against the live save. Before any migration work:

1. Create an application-level SQLite backup.
2. Copy representative legacy data into an isolated `FOOTY_DATA_DIR`.
3. Run upgrade and integrity checks there.
4. Repair the empty baseline before documenting Alembic as the sole installation path.

## Tests

With a working virtual environment:

```powershell
$env:PYTHONPATH="$PWD\backend\src"
$env:FOOTY_DATA_DIR="$PWD\.test-data"
pytest backend/tests -q --basetemp .pytest-tmp

cd frontend
npm test -- --runInBand
npm run build
```

Reproduced results on this host:

```text
Backend with host WSL access: 95 passed, 9 skipped in 210.69s
Frontend Jest:                2 suites, 6 tests passed
TypeScript/Vite build:        passed
```

If a restricted shell blocks WSL, GRF integration tests can fail with `E_ACCESSDENIED` before the engine starts. Confirm with `wsl --status` and rerun in a normal host terminal.

## Benchmark

```powershell
python backend/benchmarks/run_benchmark.py --smoke
```

Smoke mode is a synthetic harness check. Full mode currently executes fixtures sequentially and ignores worker count for execution. Neither mode is a valid worker-scaling baseline yet.

## Docker

```powershell
docker compose up --build
```

The compose file exposes the frontend on port 80 and backend on 5001, with data/report volumes. GRF/WSL/GPU compatibility is host-specific and is not certified by the compose file alone.
