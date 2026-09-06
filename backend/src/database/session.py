from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager, closing
import os
import sqlite3
import tempfile
from database.models import Base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR_OVERRIDE = os.environ.get("FOOTY_DATA_DIR")
if _DATA_DIR_OVERRIDE:
    DB_FILE = os.path.join(_DATA_DIR_OVERRIDE, "football_sim.db")
else:
    DB_FILE = os.path.join(BASE_DIR, "..", "..", "data", "football_sim.db")
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
db_url = f"sqlite:///{DB_FILE}"

engine = create_engine(db_url, connect_args={"check_same_thread": False, "timeout": 30.0})

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

def backup_database(destination: str) -> None:
    """Create a transactionally consistent SQLite snapshot, including WAL data."""
    destination_path = os.path.abspath(destination)
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    fd, staging_path = tempfile.mkstemp(
        prefix=".footy-backup-", suffix=".db", dir=os.path.dirname(destination_path)
    )
    os.close(fd)
    try:
        with closing(sqlite3.connect(DB_FILE, timeout=30.0)) as source, closing(
            sqlite3.connect(staging_path, timeout=30.0)
        ) as target:
            source.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise RuntimeError(f"Backup integrity check failed: {integrity}")
        os.replace(staging_path, destination_path)
    finally:
        if os.path.exists(staging_path):
            os.unlink(staging_path)


def restore_database(source_path: str) -> None:
    """Restore a verified SQLite snapshot while invalidating pooled connections."""
    source_path = os.path.abspath(source_path)
    if not os.path.isfile(source_path):
        raise FileNotFoundError(source_path)
    with closing(sqlite3.connect(source_path, timeout=30.0)) as source:
        integrity = source.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError(f"Save integrity check failed: {integrity}")
        engine.dispose()
        with closing(sqlite3.connect(DB_FILE, timeout=30.0)) as target:
            source.backup(target)
            target.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        engine.dispose()

def get_raw_conn(db_file=None):
    """
    Return a raw sqlite3 connection configured with FK enforcement, WAL mode, and busy timeout.
    Note: WAL mode and busy timeout reduce and gracefully handle lock contention during concurrent
    reads/writes, but SQLite still requires a single writer lock.
    """
    target_db = db_file or DB_FILE
    os.makedirs(os.path.dirname(target_db), exist_ok=True)
    conn = sqlite3.connect(target_db, timeout=30.0)
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    return conn
