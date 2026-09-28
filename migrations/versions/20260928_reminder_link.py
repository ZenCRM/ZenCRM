from alembic import op
import sqlalchemy as sa

revision = '20260928_reminder_link'
down_revision = '20260928_reminders'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    cols = [c['name'] for c in inspector.get_columns('reminders')]
    if 'link' not in cols:
        with op.batch_alter_table('reminders') as batch_op:
            batch_op.add_column(sa.Column('link', sa.String(500), nullable=True))


def downgrade():
    with op.batch_alter_table('reminders') as batch_op:
        batch_op.drop_column('link')
