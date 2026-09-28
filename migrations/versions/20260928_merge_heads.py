"""Merge meeting_lead and reminder_link heads."""
from alembic import op

revision = '20260928_merge_heads'
down_revision = ('20260928_reminder_link', '20260928_meeting_lead')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
