import logging
import sqlite3
import os
from pathlib import Path

from database.session import engine, DB_FILE
from database.models import Base

logger = logging.getLogger("footy.database.setup")

def create_tables(db_file=DB_FILE):
    """Create all database tables via SQLAlchemy Base metadata and ensure new columns exist."""
    Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    # Safe SQLite column migration for Match table
    try:
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(Match);")
            cols = [col[1] for col in cur.fetchall()]
            if "simulation_run_id" not in cols:
                cur.execute("ALTER TABLE Match ADD COLUMN simulation_run_id TEXT;")
            if "video_url" not in cols:
                cur.execute("ALTER TABLE Match ADD COLUMN video_url TEXT;")
            conn.commit()
            conn.close()
    except Exception as e:
        logger.warning(f"Note on SQLite column addition: {e}")

def reset_database(db_file=DB_FILE):
    """Drop all tables for a true fresh start."""
    try:
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = OFF;")
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [r[0] for r in cur.fetchall()]
            for t in tables:
                cur.execute(f'DROP TABLE IF EXISTS "{t}";')
            conn.commit()
            cur.execute("VACUUM;")
            conn.close()
    except Exception as e:
        logger.warning(f"Direct SQLite drop note: {e}")
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        pass
    logger.info("Database reset completed - all tables dropped!")

def initialize_fresh_database(db_file=DB_FILE):
    """Initialize database ensuring all tables exist."""
    logger.info("Initializing database tables...")
    create_tables(db_file)
    logger.info("Database initialization completed!")

def init_simulation_run(season_year: int = 2026, render_mode: str = "3d", total_matches: int = 380) -> str:
    """
    Initializes a new isolated simulation run with a unique run_id.
    Creates run-scoped storage directory under RECORDINGS_DIR / run_id.
    Persists SimulationRun record to SQLite.
    """
    import time
    import uuid
    from datetime import datetime, timezone
    from config import RECORDINGS_DIR
    from database.session import get_db_session
    from database.models import SimulationRun

    create_tables()

    run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    run_dir = RECORDINGS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    with get_db_session() as db:
        # Mark any previous running runs as archived/cancelled
        db.query(SimulationRun).filter(SimulationRun.status == "running").update({"status": "archived"})
        new_run = SimulationRun(
            run_id=run_id,
            season_year=season_year,
            created_at=datetime.now(timezone.utc).isoformat(),
            status="running",
            render_mode=render_mode,
            total_matches=total_matches,
            matches_played=0
        )
        db.add(new_run)
        db.commit()

    logger.info(f"Initialized simulation run: {run_id} (season={season_year}, render_mode={render_mode})")
    return run_id

def get_current_simulation_run() -> str:
    """Returns the most recent active or completed simulation run_id."""
    from database.session import get_db_session
    from database.models import SimulationRun
    try:
        with get_db_session() as db:
            run = db.query(SimulationRun).order_by(SimulationRun.created_at.desc()).first()
            if run:
                return run.run_id
    except Exception as e:
        logger.debug("Failed to query SimulationRun: %s", e)
    return "default"

def clean_old_simulation_data(preserve_run_id: str = None):
    """
    Safely purges previous simulation run directories and old reports.
    Preserves active run directory if specified.
    """
    import shutil
    from config import RECORDINGS_DIR, REPORTS_DIR

    logger.info(f"Purging old simulation run directories (preserving: {preserve_run_id})...")

    # 1. Clean run directories in RECORDINGS_DIR
    if RECORDINGS_DIR.exists():
        for item in RECORDINGS_DIR.iterdir():
            if item.is_dir() and item.name.startswith("run_"):
                if item.name != preserve_run_id:
                    logger.info(f"Purging old simulation run directory: {item.name}")
                    try:
                        shutil.rmtree(item)
                    except Exception as e:
                        logger.error(f"Failed to remove run directory {item}: {e}")
            elif item.is_file() and not item.name.startswith("."):
                try:
                    item.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove top-level file {item.name}: {e}")

    # 2. Clear old season reports
    for rep in REPORTS_DIR.glob("season_*.json"):
        try:
            rep.unlink()
        except Exception as e:
            logger.warning(f"Could not remove old report {rep.name}: {e}")

    overview = REPORTS_DIR / "seasons_overview.json"
    if overview.exists():
        try:
            overview.unlink()
        except Exception as e:
            logger.warning(f"Could not remove seasons_overview.json: {e}")

    # 3. Clear transfer logs
    trans_dir = REPORTS_DIR / "transfer_logs"
    if trans_dir.exists():
        for tf in trans_dir.glob("*.txt"):
            try:
                tf.unlink()
            except Exception as e:
                logger.warning(f"Could not remove transfer log {tf.name}: {e}")

    logger.info("Cleaned up old simulation data successfully!")

if __name__ == '__main__':
    create_tables()
    print("Tables created successfully in", DB_FILE)
