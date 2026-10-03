"""Record when a phone claims an SMS queue task and index task status

Revision ID: 0002_sms_queue_claimed_at
Revises: 0001_baseline
Create Date: 2026-10-03 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_sms_queue_claimed_at'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('sms_queue', schema=None) as batch_op:
        batch_op.add_column(sa.Column('claimed_at', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_sms_queue_status'), ['status'], unique=False)


def downgrade():
    with op.batch_alter_table('sms_queue', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_sms_queue_status'))
        batch_op.drop_column('claimed_at')
