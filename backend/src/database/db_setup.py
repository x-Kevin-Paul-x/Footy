import logging
import sqlite3
import os
from pathlib import Path

from database.session import engine, DB_FILE
from database.models import Base

logger = logging.getLogger("footy.database.setup")

def create_tables(db_file=DB_FILE):
    """Create all database tables via SQLAlchemy Base metadata."""
    Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

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

def clean_old_simulation_data():
    """Purge old recordings, traces, season reports, and transfer logs for a clean new simulation run."""
    from config import RECORDINGS_DIR, REPORTS_DIR
    logger.info("Purging old simulation recordings, reports, and logs...")

    # 1. Clear recordings directory
    if RECORDINGS_DIR.exists():
        for item in RECORDINGS_DIR.iterdir():
            if item.is_file() and not item.name.startswith("."):
                try:
                    item.unlink()
                except Exception:
                    pass

    # 2. Clear season reports
    for rep in REPORTS_DIR.glob("season_*.json"):
        try:
            rep.unlink()
        except Exception:
            pass

    overview = REPORTS_DIR / "seasons_overview.json"
    if overview.exists():
        try:
            overview.unlink()
        except Exception:
            pass

    # 3. Clear transfer logs
    trans_dir = REPORTS_DIR / "transfer_logs"
    if trans_dir.exists():
        for tf in trans_dir.glob("*.txt"):
            try:
                tf.unlink()
            except Exception:
                pass

    logger.info("Cleaned up old simulation data successfully!")

if __name__ == '__main__':
    create_tables()
    print("Tables created successfully in", DB_FILE)
