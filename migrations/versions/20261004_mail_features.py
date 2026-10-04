"""HTML mail, lazy attachments and recipient fields."""
from alembic import op
import sqlalchemy as sa

revision = '20261004_mail_features'
down_revision = '20261004_mailboxes'
branch_labels = None
depends_on = None


def upgrade():
    fields = {
        'mailboxes': [sa.Column('signature_format', sa.String(10), nullable=False, server_default='text')],
        'mail_messages': [
            sa.Column('cc', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('bcc', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('body_html', sa.Text(), nullable=False, server_default=''),
            sa.Column('attachments', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('content_version', sa.Integer(), nullable=False, server_default='0'),
        ],
    }
    for table, columns in fields.items():
        existing = {c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}
        with op.batch_alter_table(table) as batch:
            for column in columns:
                if column.name not in existing:
                    batch.add_column(column)
    # Migration defaults also cover upgraded rows; models use application defaults.
    for table, columns in fields.items():
        with op.batch_alter_table(table) as batch:
            for column in columns:
                batch.alter_column(column.name, server_default=None)


def downgrade():
    with op.batch_alter_table('mail_messages') as batch:
        for name in ('content_version', 'attachments', 'body_html', 'bcc', 'cc'):
            batch.drop_column(name)
    with op.batch_alter_table('mailboxes') as batch:
        batch.drop_column('signature_format')
