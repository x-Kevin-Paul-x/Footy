"""Cross-process coordination for acceptance and database replacement."""
from pathlib import Path

from filelock import FileLock


def administration_lock():
    from database.session import DB_FILE
    return FileLock(str(Path(DB_FILE).with_suffix('.admin.lock')), timeout=30)
