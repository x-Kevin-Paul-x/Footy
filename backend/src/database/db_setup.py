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
            cur.execute("PRAGMA table_info(SimulationRun);")
            run_cols = {col[1] for col in cur.fetchall()}
            for column_name, definition in (
                ("started_at", "TEXT"),
                ("finished_at", "TEXT"),
                ("heartbeat_at", "TEXT"),
                ("cancel_requested", "INTEGER NOT NULL DEFAULT 0"),
                ("error_message", "TEXT"),
            ):
                if column_name not in run_cols:
                    cur.execute(f"ALTER TABLE SimulationRun ADD COLUMN {column_name} {definition};")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_match_season_number ON Match(season_year, match_number);")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_match_teams ON Match(season_year, home_team_id, away_team_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_match_sim_run_id ON Match(simulation_run_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_matchevent_match_id ON MatchEvent(match_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_transfer_season_year ON TransferHistory(season_year);")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_player_team_id ON Player(team_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_attr_player_id ON PlayerAttribute(player_id);")
            conn.commit()
            conn.close()
    except Exception as e:
        logger.warning(f"Note on SQLite column/index addition: {e}")

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

    now = datetime.now(timezone.utc).isoformat()
    with get_db_session() as db:
        # A running row cannot survive a process restart. Preserve the record and
        # make the interruption explicit instead of presenting it as archived.
        db.query(SimulationRun).filter(SimulationRun.status == "running").update({
            "status": "interrupted", "finished_at": now,
            "error_message": "API process restarted before the run completed",
        })
        new_run = SimulationRun(
            run_id=run_id,
            season_year=season_year,
            created_at=now,
            started_at=now,
            heartbeat_at=now,
            status="running",
            render_mode=render_mode,
            total_matches=total_matches,
            matches_played=0
        )
        db.add(new_run)
        db.commit()

    logger.info(f"Initialized simulation run: {run_id} (season={season_year}, render_mode={render_mode})")
    return run_id


def update_simulation_run(run_id: str, **updates) -> None:
    """Atomically update durable run state from API or simulation workers."""
    from datetime import datetime, timezone
    from database.session import get_db_session
    from database.models import SimulationRun

    allowed = {
        "status", "matches_played", "cancel_requested", "error_message",
        "started_at", "finished_at", "heartbeat_at", "metadata_json",
    }
    values = {key: value for key, value in updates.items() if key in allowed}
    values.setdefault("heartbeat_at", datetime.now(timezone.utc).isoformat())
    with get_db_session() as db:
        changed = db.query(SimulationRun).filter(SimulationRun.run_id == run_id).update(values)
        if not changed:
            raise KeyError(f"Unknown simulation run: {run_id}")


def simulation_cancel_requested(run_id: str) -> bool:
    from database.session import get_db_session
    from database.models import SimulationRun
    with get_db_session() as db:
        value = db.query(SimulationRun.cancel_requested).filter(
            SimulationRun.run_id == run_id
        ).scalar()
        return bool(value)


def recover_interrupted_runs() -> int:
    """Mark jobs left running by a previous process as interrupted."""
    from datetime import datetime, timezone
    from database.session import get_db_session
    from database.models import SimulationRun
    now = datetime.now(timezone.utc).isoformat()
    with get_db_session() as db:
        return db.query(SimulationRun).filter(SimulationRun.status == "running").update({
            "status": "interrupted",
            "finished_at": now,
            "heartbeat_at": now,
            "error_message": "API process stopped before the run completed",
        })

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
    import time
    from config import RECORDINGS_DIR

    logger.info("Applying simulation artifact retention policy (preserving: %s)", preserve_run_id)

    # Keep historical runs by default. Operators can opt into a count-based
    # policy; transient files are only removed after a grace period so an active
    # worker is never mistaken for stale output.
    retention = max(0, int(os.environ.get("FOOTY_RUN_RETENTION", "0")))
    run_dirs = sorted(
        (p for p in RECORDINGS_DIR.glob("run_*") if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ) if RECORDINGS_DIR.exists() else []
    retained = 0
    for run_dir in run_dirs:
        if run_dir.name == preserve_run_id:
            continue
        retained += 1
        if retention and retained > retention:
            logger.info("Removing run outside configured retention: %s", run_dir.name)
            shutil.rmtree(run_dir)

    stale_before = time.time() - float(os.environ.get("FOOTY_TEMP_MAX_AGE_SECONDS", "86400"))
    if RECORDINGS_DIR.exists():
        for item in RECORDINGS_DIR.iterdir():
            if (
                item.is_file()
                and item.stat().st_mtime < stale_before
                and (item.suffix in {".tmp", ".dump"} or item.name.startswith(("payload_", "run_grf_")))
            ):
                try:
                    item.unlink()
                except OSError as exc:
                    logger.warning("Could not remove stale temporary file %s: %s", item.name, exc)
    logger.info("Simulation artifact retention policy complete")

if __name__ == '__main__':
    create_tables()
    print("Tables created successfully in", DB_FILE)
