"""Persist squad jersey numbers."""
from alembic import op
import sqlalchemy as sa

revision = 'f42b8a7091c3'
down_revision = '879f4c01467a'
branch_labels = None
depends_on = None


def upgrade():
    if 'jersey_number' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('Player')}:
        with op.batch_alter_table('Player') as batch:
            batch.add_column(sa.Column('jersey_number', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('Player') as batch:
        batch.drop_column('jersey_number')
