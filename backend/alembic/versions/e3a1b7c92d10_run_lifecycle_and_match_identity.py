"""add durable run lifecycle and run-scoped match identity

Revision ID: e3a1b7c92d10
Revises: dc914aadd948
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e3a1b7c92d10"
down_revision: Union[str, Sequence[str], None] = "dc914aadd948"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    run_columns = {column["name"] for column in inspector.get_columns("SimulationRun")}
    additions = {
        "started_at": sa.Column("started_at", sa.String(), nullable=True),
        "finished_at": sa.Column("finished_at", sa.String(), nullable=True),
        "heartbeat_at": sa.Column("heartbeat_at", sa.String(), nullable=True),
        "cancel_requested": sa.Column(
            "cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        "error_message": sa.Column("error_message", sa.String(), nullable=True),
    }
    missing = [column for name, column in additions.items() if name not in run_columns]
    if missing:
        with op.batch_alter_table("SimulationRun") as batch_op:
            for column in missing:
                batch_op.add_column(column)

    match_columns = {column["name"] for column in inspector.get_columns("Match")}
    missing_match = []
    if "simulation_run_id" not in match_columns:
        missing_match.append(sa.Column("simulation_run_id", sa.String(), nullable=True))
    if "video_url" not in match_columns:
        missing_match.append(sa.Column("video_url", sa.String(), nullable=True))
    if missing_match:
        with op.batch_alter_table("Match") as batch_op:
            for column in missing_match:
                batch_op.add_column(column)

    duplicates = bind.execute(sa.text(
        "SELECT simulation_run_id, season_year, match_number FROM Match "
        "WHERE simulation_run_id IS NOT NULL "
        "GROUP BY simulation_run_id, season_year, match_number HAVING COUNT(*) > 1"
    )).fetchall()
    if duplicates:
        raise RuntimeError(
            "Run-scoped match duplicates must be reconciled before migration: "
            f"{[(row[0], row[1], row[2]) for row in duplicates]}"
        )

    unique_names = {
        constraint.get("name") for constraint in sa.inspect(bind).get_unique_constraints("Match")
    }
    if "uq_match_run_season_number" not in unique_names:
        with op.batch_alter_table("Match") as batch_op:
            batch_op.create_unique_constraint(
                "uq_match_run_season_number",
                ["simulation_run_id", "season_year", "match_number"],
            )


def downgrade() -> None:
    # Lifecycle metadata and identity constraints protect persisted runs. Keep them
    # when downgrading application code rather than deleting operational history.
    return
