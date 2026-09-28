"""Add notes to synchronized phone calls."""
from alembic import op
import sqlalchemy as sa

revision = '20260928_phone_call_note'
down_revision = '20260927_notes'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('phone_calls', sa.Column('note', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('phone_calls') as batch:
        batch.drop_column('note')
