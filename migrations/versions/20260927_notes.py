"""Typed notes for calls and emails."""
from alembic import op
import sqlalchemy as sa

revision = '20260927_notes'
down_revision = '4ed6a32508a7'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('comments', sa.Column('kind', sa.String(16), nullable=False, server_default='note'))
    op.add_column('comments', sa.Column('communication_status', sa.String(16)))
    op.add_column('comments', sa.Column('address', sa.String(254)))

def downgrade():
    with op.batch_alter_table('comments') as batch:
        batch.drop_column('address')
        batch.drop_column('communication_status')
        batch.drop_column('kind')
