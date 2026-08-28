import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")
REPORTS_DIR = BACKEND_DIR / "reports"
SEASON_REPORTS_DIR = REPORTS_DIR / "season_reports"
MATCH_REPORTS_DIR = REPORTS_DIR / "match_reports"
TRANSFER_LOGS_DIR = REPORTS_DIR / "transfer_logs"
RECORDINGS_DIR = REPORTS_DIR / "recordings"
ML_REPORTS_DIR = REPORTS_DIR / "ml_reports"
ML_MODELS_DIR = BASE_DIR / "ml" / "models"
DATA_DIR = Path(os.environ.get("FOOTY_DATA_DIR") or (BACKEND_DIR / "data"))
SIMULATION_SCRIPT = BASE_DIR / "main.py"

LOCAL_CHECKPOINTS_DIR = BACKEND_DIR / "checkpoints" / "tikick"
TIKICK_CHECKPOINT_PATH = LOCAL_CHECKPOINTS_DIR / "actor.pt"
LOCAL_TIKICK_DIR = BACKEND_DIR / "third_party" / "tikick"
BALLER_DIR = PROJECT_ROOT.parent / "Baller"
ENGINE_MODE = os.getenv("FOOTY_ENGINE_MODE", "AUTO")  # Options: AUTO, GRF, HEURISTIC

API_PORT = _env_int("FOOTY_API_PORT", 5001)
API_DEBUG = _env_bool("FOOTY_API_DEBUG", True)
SIMULATION_TIMEOUT_SECONDS = _env_int("FOOTY_SIMULATION_TIMEOUT_SECONDS", 1800)
NUM_SEASONS = _env_int("FOOTY_NUM_SEASONS", 1)
FOOTY_GRF_MAX_STEPS = _env_int("FOOTY_GRF_MAX_STEPS", 1200)
FOOTY_PARALLEL_WORKERS = _env_int("FOOTY_PARALLEL_WORKERS", 10)


def ensure_report_directories() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    SEASON_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    MATCH_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TRANSFER_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    ML_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _sweep_stale_temp_files()


_TEMP_FILE_PATTERNS = ("run_grf_*.py", "run_render_*.py", "payload_*.json", "progress_*.json")


def _sweep_stale_temp_files(directory: Path = None, max_age_seconds: int = 6 * 3600) -> int:
    """Delete leftover GRF runner scripts/payloads older than max_age_seconds.

    WSL subprocess failures or timeouts can leave these behind (M10 fix); they are
    cleaned eagerly in finally-blocks, and this sweep is a safety net on startup.
    """
    target = directory or RECORDINGS_DIR
    if not target.exists():
        return 0
    cutoff = time.time() - max_age_seconds
    removed = 0
    for pattern in _TEMP_FILE_PATTERNS:
        for f in target.glob(pattern):
            try:
                if f.is_file() and f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
            except OSError:
                continue
    if removed:
        logging.getLogger("footy.config").info("Swept %d stale temp file(s) from %s", removed, target)
    return removed