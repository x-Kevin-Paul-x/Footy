from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os
from database.models import Base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR_OVERRIDE = os.environ.get("FOOTY_DATA_DIR")
if _DATA_DIR_OVERRIDE:
    DB_FILE = os.path.join(_DATA_DIR_OVERRIDE, "football_sim.db")
else:
    DB_FILE = os.path.join(BASE_DIR, "..", "..", "data", "football_sim.db")
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
db_url = f"sqlite:///{DB_FILE}"

engine = create_engine(db_url, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
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

import sqlite3

def get_raw_conn(db_file=None):
    """Return a raw sqlite3 connection configured with FK enforcement, WAL mode, and busy timeout."""
    target_db = db_file or DB_FILE
    os.makedirs(os.path.dirname(target_db), exist_ok=True)
    conn = sqlite3.connect(target_db, timeout=10.0)
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn
