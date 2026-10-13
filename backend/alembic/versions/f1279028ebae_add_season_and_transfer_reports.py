"""Frozen additive SQLite baseline, including the original report tables.

Existing stamped installations retain history. Fresh and unversioned databases
receive the frozen table set; later revisions reconcile existing schemas.
"""
import json
from pathlib import Path
from alembic import op
import sqlalchemy as sa

revision = "f1279028ebae"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    baseline = json.loads((Path(__file__).parents[1] / "schema_baseline.json").read_text(encoding="utf-8"))
    for table in baseline:
        if table["name"] not in existing:
            bind.exec_driver_sql(table["sql"])
            for index in table["indexes"]:
                bind.exec_driver_sql(index)


def downgrade():
    raise RuntimeError("Baseline downgrade would delete saved campaigns; restore a verified backup instead")
