import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure backend/src and project root are in sys.path
TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent
BACKEND_SRC = BACKEND_DIR / "src"
PROJECT_ROOT = BACKEND_DIR.parent

for p in [str(BACKEND_SRC), str(BACKEND_DIR), str(PROJECT_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# --- Isolated data dir for every test run (M9) ----------------------------
# Set BEFORE importing any module that reads config/session so DB_FILE
# resolves to a throwaway temp folder instead of backend/data/football_sim.db.
_TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="footy_test_data_"))
os.environ["FOOTY_DATA_DIR"] = str(_TEST_DATA_DIR)


@pytest.fixture(scope="session", autouse=True)
def _isolated_data_dir():
    """Point DB/save paths at a temp dir and clean it up after the run."""
    import database.session as session_mod
    import database.models as models_mod
    import config as config_mod

    # Main DB lives in the temp dir via the FOOTY_DATA_DIR override.
    session_mod.DB_FILE = str(_TEST_DATA_DIR / "football_sim.db")
    session_mod.db_url = f"sqlite:///{session_mod.DB_FILE}"
    session_mod.os.makedirs(os.path.dirname(session_mod.DB_FILE), exist_ok=True)
    session_mod.engine = session_mod.create_engine(
        session_mod.db_url, connect_args={"check_same_thread": False}
    )
    session_mod.SessionLocal.configure(bind=session_mod.engine)
    session_mod.Base.metadata.create_all(bind=session_mod.engine)

    config_mod.DATA_DIR = _TEST_DATA_DIR

    # api_fastapi captures DB_FILE/SAVES_DIR at import time; re-point them.
    import api_fastapi as api_mod
    api_mod.DB_FILE = session_mod.DB_FILE
    api_mod.SAVES_DIR = _TEST_DATA_DIR / "saves"
    api_mod.SAVES_DIR.mkdir(parents=True, exist_ok=True)

    yield

    shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True)
