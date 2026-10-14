import logging
import sqlite3
import os
from pathlib import Path

from database.session import engine, DB_FILE
from database.models import Base

logger = logging.getLogger("footy.database.setup")

def create_tables(db_file=None):
    """Apply the versioned schema; never silently patch columns at runtime."""
    from database import session
    from database.migrations import upgrade_database
    if db_file and Path(db_file).resolve() != Path(session.DB_FILE).resolve():
        from sqlalchemy import create_engine
        target = create_engine(f"sqlite:///{Path(db_file).resolve().as_posix()}")
        try:
            upgrade_database(target)
        finally:
            target.dispose()
    else:
        upgrade_database(session.engine)


def reset_database(db_file=DB_FILE, *, allow_reset=False):
    """Explicit administrative reset, never part of normal startup."""
    if not allow_reset:
        raise RuntimeError("Database reset requires allow_reset=True and an isolated data directory")
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

    clean_old_simulation_data(preserve_run_id=run_id)
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


def complete_simulation_run(run_id: str) -> None:
    """Finalize progress from persisted fixtures, never a stale halftime counter."""
    from datetime import datetime, timezone
    from database.session import get_db_session
    from database.models import SimulationRun, Match
    with get_db_session() as db:
        run = db.query(SimulationRun).filter(SimulationRun.run_id == run_id).one()
        run.matches_played = db.query(Match).filter(Match.simulation_run_id == run_id).count()
        run.status = 'completed'
        run.finished_at = datetime.now(timezone.utc).isoformat()
        run.heartbeat_at = run.finished_at
        run.error_message = None


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

def clean_old_simulation_data(preserve_run_id: str = None, recordings_dir: Path = None):
    """
    Safely purges previous simulation run directories and old reports.
    Preserves the new run. By default, no previous run recordings are retained.
    Curated repository assets live outside this runtime directory.
    """
    import shutil
    import time
    from config import RECORDINGS_DIR

    logger.info("Applying simulation artifact retention policy (preserving: %s)", preserve_run_id)

    recordings_root = Path(recordings_dir or RECORDINGS_DIR).resolve()
    # Zero means zero previous runs, rather than unlimited historical storage.
    # A positive override keeps that many additional runs for diagnostics.
    retention = max(0, int(os.environ.get("FOOTY_RUN_RETENTION", "0")))
    run_dirs = sorted(
        (p for p in recordings_root.glob("run_*") if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ) if recordings_root.exists() else []
    retained = 0
    import json
    pinned = set()
    for manifest in (Path(DB_FILE).parent / 'saves').glob('*.manifest.json'):
        try:
            pinned.update(json.loads(manifest.read_text(encoding='utf-8')).get('run_ids', []))
        except (OSError, ValueError, TypeError):
            logger.warning('Cannot read save retention manifest %s', manifest.name)
    for run_dir in run_dirs:
        if run_dir.name == preserve_run_id or run_dir.name in pinned:
            continue
        retained += 1
        if retained > retention:
            if run_dir.is_symlink() or run_dir.resolve().parent != recordings_root:
                raise ValueError(f"Refusing to delete recordings outside {recordings_root}: {run_dir}")
            logger.info("Removing run outside configured retention: %s", run_dir.name)
            shutil.rmtree(run_dir)

    stale_before = time.time() - float(os.environ.get("FOOTY_TEMP_MAX_AGE_SECONDS", "86400"))
    if recordings_root.exists():
        for item in recordings_root.iterdir():
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
