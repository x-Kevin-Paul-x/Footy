import os
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
ML_REPORTS_DIR = PROJECT_ROOT / "ml" / "reports"
SIMULATION_SCRIPT = BASE_DIR / "main.py"

API_PORT = _env_int("FOOTY_API_PORT", 5001)
API_DEBUG = _env_bool("FOOTY_API_DEBUG", True)
SIMULATION_TIMEOUT_SECONDS = _env_int("FOOTY_SIMULATION_TIMEOUT_SECONDS", 1800)
NUM_SEASONS = _env_int("FOOTY_NUM_SEASONS", 10)


def ensure_report_directories() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    SEASON_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    MATCH_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TRANSFER_LOGS_DIR.mkdir(parents=True, exist_ok=True)