"""Scheduled mailbox polling."""
from alembic import op
import sqlalchemy as sa

revision = '20261004_mail_polling'
down_revision = '20261004_email_preference'
branch_labels = None
depends_on = None


def upgrade():
    columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('mailboxes')}
    with op.batch_alter_table('mailboxes') as batch:
        for column in (sa.Column('sync_interval_minutes',sa.Integer(),nullable=False,server_default='5'),
                       sa.Column('next_sync_at',sa.DateTime()),
                       sa.Column('sync_claim_token',sa.String(36)),
                       sa.Column('sync_claim_until',sa.DateTime())):
            if column.name not in columns:
                batch.add_column(column)


def downgrade():
    with op.batch_alter_table('mailboxes') as batch:
        for name in ('sync_claim_until','sync_claim_token','next_sync_at','sync_interval_minutes'):
            batch.drop_column(name)
