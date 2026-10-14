"""Preserve campaign reports, finances and world snapshots per run."""
from alembic import op
import sqlalchemy as sa

revision = 'b20261013'
down_revision = 'a20261013'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    player_columns = {c['name'] for c in sa.inspect(bind).get_columns('Player')}
    if not {'availability_json', 'contract_json'}.issubset(player_columns):
        with op.batch_alter_table('Player') as batch:
            for name in ('availability_json', 'contract_json'):
                if name not in player_columns:
                    batch.add_column(sa.Column(name, sa.String(), nullable=True))
    for table, target_name in [('SeasonReport', 'uq_season_report_run_year'), ('TransferReport', 'uq_transfer_report_run_year')]:
        inspector = sa.inspect(bind)
        columns = {c['name'] for c in inspector.get_columns(table)}
        constraints = inspector.get_unique_constraints(table)
        with op.batch_alter_table(table, naming_convention={'uq': 'uq_%(table_name)s_%(column_0_name)s'}) as batch:
            if 'simulation_run_id' not in columns:
                batch.add_column(sa.Column('simulation_run_id', sa.String(), nullable=True))
            for constraint in constraints:
                if constraint['column_names'] == ['season_year']:
                    batch.drop_constraint(constraint['name'] or f'uq_{table}_season_year', type_='unique')
            if target_name not in {c['name'] for c in constraints}:
                batch.create_unique_constraint(target_name, ['simulation_run_id', 'season_year'])
            if not any(f['constrained_columns'] == ['simulation_run_id'] for f in inspector.get_foreign_keys(table)):
                batch.create_foreign_key(f'fk_{table}_run', 'SimulationRun', ['simulation_run_id'], ['run_id'])
    if 'simulation_run_id' not in {c['name'] for c in sa.inspect(bind).get_columns('TransferHistory')}:
        with op.batch_alter_table('TransferHistory') as batch:
            batch.add_column(sa.Column('simulation_run_id', sa.String(), nullable=True))
            batch.create_foreign_key('fk_transfer_run', 'SimulationRun', ['simulation_run_id'], ['run_id'])
    if 'FinancialEntry' not in sa.inspect(bind).get_table_names():
        op.create_table('FinancialEntry',
            sa.Column('entry_id', sa.Integer(), primary_key=True),
            sa.Column('run_id', sa.String(), sa.ForeignKey('SimulationRun.run_id'), nullable=False),
            sa.Column('team_name', sa.String(), nullable=False),
            sa.Column('season_year', sa.Integer(), nullable=False),
            sa.Column('entry_number', sa.Integer(), nullable=False),
            sa.Column('category', sa.String(), nullable=False),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('balance', sa.Float(), nullable=False),
            sa.Column('description', sa.String(), nullable=False),
            sa.UniqueConstraint('run_id', 'team_name', 'entry_number', name='uq_finance_entry'))
    if 'CampaignSnapshot' not in sa.inspect(bind).get_table_names():
        op.create_table('CampaignSnapshot',
            sa.Column('run_id', sa.String(), sa.ForeignKey('SimulationRun.run_id'), primary_key=True),
            sa.Column('season_year', sa.Integer(), primary_key=True),
            sa.Column('matches_played', sa.Integer(), nullable=False),
            sa.Column('state_json', sa.String(), nullable=False),
            sa.Column('created_at', sa.String(), nullable=False))


def downgrade():
    raise RuntimeError('Campaign history is retained; restore a verified backup for rollback')
