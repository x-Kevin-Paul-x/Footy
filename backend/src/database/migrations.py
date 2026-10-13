"""Apply the checked-in migration history without runtime schema patches."""
import threading
import sqlite3
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

_lock = threading.Lock()


def upgrade_database(engine):
    backend = Path(__file__).resolve().parents[2]
    configuration = Config(str(backend / "alembic.ini"))
    configuration.set_main_option("script_location", str(backend / "alembic"))
    target_path = Path(engine.url.database)
    if target_path.is_file() and target_path.stat().st_size:
        # The backup API includes committed WAL pages; a filesystem copy does not.
        with sqlite3.connect(str(target_path)) as source:
            stamped = source.execute("SELECT name FROM sqlite_master WHERE name='alembic_version'").fetchone()
            current = source.execute('SELECT version_num FROM alembic_version').fetchone() if stamped else None
            if not current or current[0] != ScriptDirectory.from_config(configuration).get_current_head():
                backup_path = target_path.with_name(target_path.stem + '.pre-migration-' + uuid.uuid4().hex[:8] + '.db')
                with sqlite3.connect(str(backup_path)) as backup:
                    source.backup(backup)
                    if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise RuntimeError('Pre-migration backup failed its integrity check')
    with _lock, engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        try:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            configuration.attributes["connection"] = connection
            command.upgrade(configuration, "head")
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"Migration rejected: foreign key violations: {violations[:10]}")
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def main():
    from database.session import engine
    upgrade_database(engine)
