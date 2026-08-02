from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os
from database.models import Base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
