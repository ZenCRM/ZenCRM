"""Files attached to CRM records."""
from alembic import op
import sqlalchemy as sa

revision = '20260929_attachments'
down_revision = '20260928_merge_heads'
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table('attachments'):
        return
    op.create_table('attachments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('entity_type', sa.String(20), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('storage_name', sa.String(64), nullable=False, unique=True),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_index('ix_attachments_entity_type', 'attachments', ['entity_type'])
    op.create_index('ix_attachments_entity_id', 'attachments', ['entity_id'])


def downgrade():
    op.drop_index('ix_attachments_entity_id', table_name='attachments')
    op.drop_index('ix_attachments_entity_type', table_name='attachments')
    op.drop_table('attachments')
