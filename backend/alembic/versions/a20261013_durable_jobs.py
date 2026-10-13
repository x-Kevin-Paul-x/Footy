"""Persist accepted jobs and unique active ownership."""
from alembic import op
import sqlalchemy as sa

revision = 'a20261013'
down_revision = 'f42b8a7091c3'
branch_labels = None
depends_on = None


def upgrade():
    if 'WorkJob' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table('WorkJob',
        sa.Column('job_id', sa.String(), primary_key=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('active_key', sa.String(), nullable=True, unique=True),
        sa.Column('request_key', sa.String(), nullable=True),
        sa.Column('run_id', sa.String(), sa.ForeignKey('SimulationRun.run_id')),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('started_at', sa.String()), sa.Column('finished_at', sa.String()),
        sa.Column('lease_owner', sa.String()), sa.Column('lease_until', sa.Float()),
        sa.Column('cancel_requested', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('payload_json', sa.String(), nullable=False),
        sa.Column('result_json', sa.String()), sa.Column('error_message', sa.String()),
        sa.UniqueConstraint('kind', 'request_key', name='uq_job_request'))


def downgrade():
    raise RuntimeError('Job history is retained; restore a backup for schema rollback')
