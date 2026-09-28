"""Allow meetings to belong to leads."""
from alembic import op
import sqlalchemy as sa

revision = '20260928_meeting_lead'
down_revision = '20260928_roles_permissions'
branch_labels = None
depends_on = None


def upgrade():
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('meetings')}
    if 'lead_id' not in columns:
        with op.batch_alter_table('meetings') as batch:
            batch.add_column(sa.Column('lead_id', sa.Integer(), sa.ForeignKey('leads.id'), nullable=True))


def downgrade():
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('meetings')}
    if 'lead_id' in columns:
        with op.batch_alter_table('meetings') as batch:
            batch.drop_column('lead_id')
