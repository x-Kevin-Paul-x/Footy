"""sync_schema_to_models

Revision ID: c7c6ac0ab9c1
Revises: f1279028ebae
Create Date: 2026-05-20 01:31:19.119278

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7c6ac0ab9c1'
down_revision: Union[str, Sequence[str], None] = 'f1279028ebae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    existing = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('Match')}
    missing = [name for name in ('home_yellow_cards', 'away_yellow_cards', 'home_red_cards', 'away_red_cards', 'home_injuries', 'away_injuries') if name not in existing]
    if missing:
        with op.batch_alter_table('Match', schema=None) as batch_op:
            for name in missing:
                batch_op.add_column(sa.Column(name, sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('Match', schema=None) as batch_op:
        batch_op.drop_column('away_injuries')
        batch_op.drop_column('home_injuries')
        batch_op.drop_column('away_red_cards')
        batch_op.drop_column('home_red_cards')
        batch_op.drop_column('away_yellow_cards')
        batch_op.drop_column('home_yellow_cards')
