"""Personal reminders."""
from alembic import op
import sqlalchemy as sa

revision = '20260928_reminders'
down_revision = '20260928_roles_permissions'
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table('reminders'):
        return
    op.create_table('reminders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('remind_at', sa.DateTime(), nullable=False),
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('tasks.id')),
        sa.Column('dismissed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'task_id', name='uq_reminder_user_task'))
    op.create_index('ix_reminders_user_id', 'reminders', ['user_id'])
    op.create_index('ix_reminders_remind_at', 'reminders', ['remind_at'])


def downgrade():
    op.drop_table('reminders')
