---
name: alembic-sqlite-guardian
description: >-
  Safe migration and schema persistence guide for SQLite using Alembic in Footy.
  Enforces batch_alter_table for SQLite compatibility, preventing table recreation crashes
  and data loss. Triggers when modifying database schemas or running migrations.
---

# SQLite & Alembic Schema Migration Guardian

This skill provides rules and best practices for managing migrations and preserving persistent league data in SQLite (`football_sim.db`).

---

## 1. SQLite Limitations & `batch_alter_table`

SQLite does not natively support `ALTER TABLE ... DROP COLUMN` or modifying existing column constraints directly without recreating the table.

### Required Alembic Migration Pattern
Always wrap table alterations in `render_as_batch=True` or use `batch_alter_table`:

```python
def upgrade() -> None:
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.add_column(sa.Column('preferred_foot', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('stamina_decay_rate', sa.Float(), server_default='1.0', nullable=False))

def downgrade() -> None:
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.drop_column('stamina_decay_rate')
        batch_op.drop_column('preferred_foot')
```

---

## 2. Migration Commands

```powershell
# Generate migration script based on models.py changes
alembic -c backend/alembic.ini revision --autogenerate -m "describe_change"

# Apply pending migrations to football_sim.db
alembic -c backend/alembic.ini upgrade head

# Rollback one migration
alembic -c backend/alembic.ini downgrade -1
```

---

## 3. Pre-Migration Data Backup Safety Rule

Before running destructive migrations on existing save games:
1. Create a backup snapshot of `football_sim.db`:
   ```powershell
   Copy-Item backend/data/football_sim.db backend/data/football_sim.db.backup
   ```
2. Verify foreign key integrity after upgrade:
   ```sql
   PRAGMA foreign_key_check;
   ```
